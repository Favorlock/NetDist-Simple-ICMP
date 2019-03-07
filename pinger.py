import select
import socket
import struct
import sys
import os
import time

icmp_echo_request = 8
icmp_packet_size = 16
timer = time.time


def checksum(string):
    count_to = (int(len(string) // 2)) * 2
    c_sum = 0
    count = 0

    lo_byte = 0
    hi_byte = 0
    while count < count_to:
        if (sys.byteorder == "little"):
            lo_byte = string[count]
            hi_byte = string[count + 1]
        else:
            lo_byte = string[count + 1]
            hi_byte = string[count]
        try:
            c_sum = c_sum + (hi_byte * 256 + lo_byte)
        except:
            c_sum = c_sum + (ord(hi_byte) * 256 + ord(lo_byte))
        count += 2

    if count_to < len(string):
        lo_byte = string[len(string) - 1]
        try:
            c_sum += lo_byte
        except:
            c_sum += ord(lo_byte)

    c_sum &= 0xffffffff

    c_sum = (c_sum >> 16) + (c_sum & 0xffff)
    c_sum += (c_sum >> 16)
    answer = ~c_sum & 0xffff
    answer = socket.htons(answer)
    return answer


def construct_packet(my_id, seq):
    # Header is type (8), code (8),checksum (16), id (16), sequence (16)
    my_checksum = 0

    header = struct.pack(
        "!BBHHH", icmp_echo_request, 0, my_checksum, my_id, seq
    )

    data = struct.pack(
        "!d", timer()
    )

    my_checksum = checksum(header + data)

    header = struct.pack(
        "!BBHHH", icmp_echo_request, 0, my_checksum, my_id, seq
    )

    return header + data


def send(my_socket, dest, my_id, seq):
    packet = construct_packet(my_id, seq)
    send_time = timer()
    my_socket.sendto(packet, (dest, 1))
    return send_time


def receive(my_socket, my_id, time_out):
    time_left = time_out / 1000
    while True:
        select_start = timer()
        inputready, outputready, exceptready = select.select([my_socket], [], [], time_left)
        select_duration = (timer() - select_start)

        if not inputready:  # Timeout
            return 0, 0, None

        packet, address = my_socket.recvfrom(2048)
        icmp_header = struct.unpack("!BBHHH", packet[20:28])

        receive_time = timer()

        if icmp_header[3] == my_id:
            packet_size = len(packet) - 28
            return (receive_time - select_start), packet_size, icmp_header

        time_left = time_left - select_duration

        if time_left <= 0:
            return 0, 0, None


def do_one(dest, my_id, seq, time_out):
    my_socket = make_socket()

    send_time = send(my_socket, dest, my_id, seq)

    if not send_time:
        0, 0, None

    result = receive(my_socket, my_id, time_out)

    my_socket.close()

    return result


def ping(host, time_out=1000):
    dest = socket.gethostbyname(host)
    my_id = os.getpid() & 0xFFFF

    transmitted = 0
    received = 0
    lost = 0
    mn = None
    mx = None
    total = None
    a = None

    print(f"PING {host} ({dest}): {icmp_packet_size} data bytes")
    for i in range(0, 1):
        result = do_one(dest, my_id, i, time_out)
        transmitted += 1
        if result[2] is not None:
            received += 1
            if not mn or result[0] < mn:
                mn = result[0]
            if not mx or result[0] > mx:
                mx = result[0]
            if not total:
                total = result[0]
            else:
                total += result[0]
            print(f"{result[1]} bytes from {dest}: icmp_seq={i}")
        else:
            lost += 1
            print("timed out")
        time.sleep(1)  # one second

    if total is not None:
        a = total / received
    else:
        mn = "na"
        a = "na"
        mx = "na"

    print(f"--- {host} ping statistics ---")
    print(f"{transmitted} packets transmitted, {received} packets received, {lost} packets lost")
    print(f"round-trip min/avg/max = {mn:.3g}/{a:.3g}/{mx:.3g} ms")


def make_socket():
    return socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)


ping("localhost")
print(" ")
ping("google.com")
