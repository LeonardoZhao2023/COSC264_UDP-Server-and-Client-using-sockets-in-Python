import socket
import datetime
import select
import sys

# Constants for protocol
MAGIC_NO = 0x36FB
DT_REQUEST = 0x0001
DT_RESPONSE = 0x0002

# Months for each language
MONTHS = {
    "English": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
    "Māori": ["Kohi-tātea", "Hui-tanguru", "Poutū-te-rangi", "Paenga-whāwhā", "Haratua", "Pipiri", "Hōngingoi", "Here-turi-kōkā", "Mahuru", "Whiringa-ā-nuku", "Whiringa-ā-rangi", "Hakihea"],
    "German": ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"],
}

# Language codes
LANGUAGE_CODES = {
    0x0001: "English",
    0x0002: "Māori",
    0x0003: "German",
}

# Extract the port numbers and validate if any of them are duplicates, not positive integers, or not in the range
# Return the port number array if valid for all, and return None otherwise
def get_valid_portnum():
    if len(sys.argv) != 4: # Validate number of command line arguments
        print("ERROR: Incorrect number of command line arguments")
        sys.exit(1)
    PortNums = []
    for arg in sys.argv[1:]: # Extract into an array and validate not integer
        try:
            port = int(arg)
            PortNums.append(port)
        except ValueError:
            print(f"ERROR: Given port '{arg}' is not a positive integer")
            return None
    if len(set(PortNums)) != 3: # Validate duplicates
        print("ERROR: Duplicate ports given")
        return None
    if any(p <= 0 for p in PortNums): # Validate not positive integer
        for p in PortNums:
            if p <= 0:
                print(f"ERROR: Given port '{p}' is not a positive integer")
        return None
    if not all(1024 <= p <= 64000 for p in PortNums): # Validate range
        for p in PortNums:
            if not (1024 <= p <= 64000):
                print(f"ERROR: Given port '{p}' is not in the range [1024, 64000]")
        return None
    return PortNums

# Creates and binds a socket to a given port for a specified language.
# Print error message and return None when a process fails
def bind_socket(port, language):
    print(f"Binding {language} to port {port}")
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    except:
        print("ERROR: Socket creation failed")
        return None
    try:
        s.bind(("localhost", port))
    except:
        print("ERROR: Socket binding failed")
        s.close()
        return None
    return s

# Validate the DT-Request packet field
def validate_field(MagicNo, PacketType, RequestType):
    if MagicNo != MAGIC_NO:
        print("ERROR: Packet magic number is incorrect, dropping packet")
        return False
    if PacketType != DT_REQUEST:
        print("ERROR: Packet is not a DT_Request, dropping packet")
        return False
    if RequestType not in [0x0001, 0x0002]:
        print("ERROR: Packet has invalid type, dropping packet")
        return False
    return True

# Formats the current date into a string according to the specified language.
def format_date(dt, lang):
    if lang == "English":
        return f"Today's date is {MONTHS[lang][dt.month - 1]} {dt.day}, {dt.year}"
    elif lang == "Māori":
        return f"Ko te rā o tēnei rā ko {MONTHS[lang][dt.month - 1]} {dt.day}, {dt.year}"
    elif lang == "German":
        return f"Heute ist der {dt.day}. {MONTHS[lang][dt.month - 1]} {dt.year}"

# Formats the current time into a string according to the specified language.
def format_time(dt, lang):
    if lang == "English":
        return f"The current time is {dt.hour:02}:{dt.minute:02}"
    elif lang == "Māori":
        return f"Ko te wā o tēnei wā {dt.hour:02}:{dt.minute:02}"
    elif lang == "German":
        return f"Die Uhrzeit ist {dt.hour:02}:{dt.minute:02}"

# Construct the DT-Response packet
def fill_packet_fields(ByteArr, LangCode, Dt, TextByte):
    ByteArr[0:2] = MAGIC_NO.to_bytes(2, "big")
    ByteArr[2:4] = DT_RESPONSE.to_bytes(2, "big")
    ByteArr[4:6] = LangCode.to_bytes(2, "big")
    ByteArr[6:8] = Dt.year.to_bytes(2, "big")
    ByteArr[8] = Dt.month
    ByteArr[9] = Dt.day
    ByteArr[10] = Dt.hour
    ByteArr[11] = Dt.minute
    ByteArr[12] = len(TextByte)
    ByteArr[13:] = TextByte

# Processes an incoming DT-Request packet and sends a DT-Response packet.
# This function performs all necessary validation and constructs the appropriate response.
def handle_request(data, addr, sock, lang_code):
    # Extract fields from the DT-Request packet
    magic_no = int.from_bytes(data[0:2], "big")
    packet_type = int.from_bytes(data[2:4], "big")
    request_type = int.from_bytes(data[4:6], "big")

    # Validate the DT-Request packet
    # Terminate the execution of the function if not valid
    if len(data) != 6:
        print("ERROR: Packet length incorrect for a DT_Request, dropping packet")
        return
    if validate_field(magic_no, packet_type, request_type) == False:
        return

    # Get current date and time
    dt = datetime.datetime.now()
    lang = LANGUAGE_CODES[lang_code]

    # Prepare the response text based on the request type (date or time)
    if request_type == 0x0001:
        text = format_date(dt, lang)
        print(f"{lang} received date request from {addr[0]}")
    else:
        text = format_time(dt, lang)
        print(f"{lang} received time request from {addr[0]}")

    text_bytes = text.encode("utf-8")
    if len(text_bytes) > 255:
        print("ERROR: Text too long, dropping packet")
        return
    
    # Prepare the DT-Response packet
    response = bytearray(13 + len(text_bytes))
    fill_packet_fields(response, lang_code, dt, text_bytes)
    
    # Send the response back to the client
    try:
        sock.sendto(response, addr)
        print("Response sent")
        return
    except:
        print("ERROR: Sending failed, dropping packet")
        return

# The main function initializes the server by binding sockets to the specified ports for each language,
# then enters an infinite loop to process incoming requests.
def main():
    # Attempt to get an array of valid port numbers
    ports = get_valid_portnum()
    if not ports:
        sys.exit(1)

    # Attempt to bind sockets for each language
    sockets = []
    for i, lang in enumerate(["English", "Māori", "German"]):
        sock = bind_socket(ports[i], lang)
        if sock is None: # Catch any failures, then close all sockets and exit
            for s in sockets:
                s.close()
            sys.exit(1)
        sockets.append(sock)
    
    # Enter an infinite loop of waiting for incoming requests on any of the sockets
    try:
        while True:
            print("Waiting for requests...")
            ready_socks, _, _ = select.select(sockets, [], []) # Wait for a request packet using select()
            for sock in ready_socks:
                sock.settimeout(1.0)
                try:
                    data, addr = sock.recvfrom(1024)
                    if sock == sockets[0]:
                        handle_request(data, addr, sock, 0x0001)  # English
                    elif sock == sockets[1]:
                        handle_request(data, addr, sock, 0x0002)  # Māori
                    elif sock == sockets[2]:
                        handle_request(data, addr, sock, 0x0003)  # German
                    else:
                        break
                except socket.timeout:
                    print("ERROR: Receiving timed out, dropping packet")
                    continue
                except:
                    print("ERROR: Receiving failed, dropping packet")
                    continue
    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        for sock in sockets:
            sock.close()
        sys.exit(1)

main()