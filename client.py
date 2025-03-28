import socket
import sys

MAGIC_NO = 0x36FB
PACKET_TYPE = 0x0001
DT_RESPONSE = 0x0002

def validate_and_get_request_type():
    # Validate and determine the request type based on the first argument (date or time)
    if len(sys.argv) != 4:
        print("ERROR: Incorrect number of command line arguments")
        sys.exit(1)
    if sys.argv[1] == "date":
        return 0x0001
    elif sys.argv[1] == "time":
        return 0x0002
    else:
        print(f"ERROR: Request type '{sys.argv[1]}' is not valid")
        sys.exit(1)

def validate_and_get_port():
    # Validate the hostname resolution
    try:
        socket.getaddrinfo(sys.argv[2], None)
    except:
        print("ERROR: Hostname resolution failed")
        sys.exit(1)
    
    # Validate the port number
    try:
        port = int(sys.argv[3])
        if port <= 0:
            print(f"ERROR: Given port '{port}' is not a positive integer")
            sys.exit(1)
        if not (1024 <= port <= 64000):
            print(f"ERROR: Given port '{port}' is not in the range [1024, 64000]")
            sys.exit(1)
        return port
    except ValueError:
        print(f"ERROR: Given port '{sys.argv[3]}' is not a positive integer")
        sys.exit(1)

def create_socket_and_connect():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1.0)
        tuple = socket.getaddrinfo(sys.argv[2], int(sys.argv[3]), family=0, type=0, flags=0)[1][4]
        sock.connect(tuple)
        return sock, tuple
    except:
        print("ERROR: Socket creation failed")
        sys.exit(1)

def send_request(sock, addr, request_type, PortNum):
    # Construct the DT-Request packet
    request = bytearray(6)
    request[0:2] = MAGIC_NO.to_bytes(2, "big")
    request[2:4] = PACKET_TYPE.to_bytes(2, "big")
    request[4:6] = request_type.to_bytes(2, "big")

    try:
        # Send the request packet to the server
        sock.sendto(request, addr)
        print(f"{sys.argv[1].capitalize()} request sent to {addr[0]}:{PortNum}")
    except:
        print("ERROR: Sending failed")
        sock.close()
        sys.exit(1)

def main():
    request_type = validate_and_get_request_type()
    port = validate_and_get_port()
    sock, addr = create_socket_and_connect()
    send_request(sock, addr, request_type, port)

    try:
        # Wait for the response from the server
        response, _ = sock.recvfrom(1024)
    except socket.timeout:
        print("ERROR: Receiving timed out")
        sock.close()
        sys.exit(1)
    except:
        print("ERROR: Receiving failed")
        sock.close()
        sys.exit(1)

    process_response(sock, response)

def process_response(sock, response):
    magic_no, packet_type, lang_code, text, text_length, day, month, year, hour, minute = extract_response_data(response, sock)
    if validate_response_packet_1(sock, response, magic_no, packet_type, lang_code, text_length):
        if validate_response_packet_2(sock, day, month, year, hour, minute):
            print_response(lang_code, text, day, month, year, hour, minute)
    sock.close()

def extract_response_data(response, sock):
    try:
        magic_no = int.from_bytes(response[0:2], "big")
        packet_type = int.from_bytes(response[2:4], "big")
        lang_code = int.from_bytes(response[4:6], "big")
        year = int.from_bytes(response[6:8], "big")
        month = response[8]
        day = response[9]
        hour = response[10]
        minute = response[11]
        text_length = response[12]
        text = response[13:13 + text_length].decode("utf-8")
        return magic_no, packet_type, lang_code, text, text_length, day, month, year, hour, minute
    except IndexError:
        print("ERROR: Packet is too small to be a DT_Response")
        sock.close()
        sys.exit(1)
    except UnicodeDecodeError:
        print("ERROR: Packet has invalid text")
        sock.close()
        sys.exit(1)

def validate_response_packet_1(sock, response, magic_no, packet_type, lang_code, text_length):
    # Validate the DT-Response packet
    if len(response) < 13:
        print("ERROR: Packet is too small to be a DT_Response")
        sock.close()
        sys.exit(1)
    if magic_no != MAGIC_NO:
        print("ERROR: Packet magic number is incorrect")
        sock.close()
        sys.exit(1)
    if packet_type != DT_RESPONSE:
        print("ERROR: Packet is not a DT_Response")
        sock.close()
        sys.exit(1)
    if lang_code not in [0x0001, 0x0002, 0x0003]:
        print("ERROR: Packet has invalid language")
        sock.close()
        sys.exit(1)
    if len(response) != 13 + text_length:
        print("ERROR: Packet text length is incorrect")
        sock.close()
        sys.exit(1)
    return True

def validate_response_packet_2(sock, day, month, year, hour, minute):
    # Validate the DT-Response packet
    if year >= 2100:
        print("ERROR: Packet has invalid year")
        sock.close()
        sys.exit(1)
    if not (1 <= month <= 12):
        print("ERROR: Packet has invalid month")
        sock.close()
        sys.exit(1)
    if not (1 <= day <= 31):
        print("ERROR: Packet has invalid day")
        sock.close()
        sys.exit(1)
    if not (0 <= hour <= 23):
        print("ERROR: Packet has invalid hour")
        sock.close()
        sys.exit(1)
    if not (0 <= minute <= 59):
        print("ERROR: Packet has invalid minute")
        sock.close()
        sys.exit(1)
    return True

def print_response(lang_code, text, day, month, year, hour, minute):
    lang_str = {0x0001: "English", 0x0002: "Māori", 0x0003: "German"}[lang_code]
    print(f"{lang_str} response received:")
    print(f"Text: {text}")
    print(f"Date: {day}/{month}/{year}")
    print(f"Time: {hour:02}:{minute:02}")

main()