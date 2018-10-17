import multiprocessing
import subprocess
import sys
import time

options = {
    "ping_count": 10,               # Determines the size of the (latency) data set to collect. Higher values will take longer but will produce more precise results
    "overlap_delay": 0.5,           # How long to wait between sent buckets of pings. This value may need to be increased to achieve accurate results on poor internet
    "bucket_size": 10,              # Number of worlds to check simultaneously. A lower value will produce more accurate results but will take longer
    "world_list_disp_cutoff": 20,   # Number of worlds to show as being fetched in command line, per line
    "show_high_latency": True,      # Whether to hide highest latency world from results
    "show_members_worlds": True,    # Whether to include members worlds when checking latency
    "show_ftp_worlds": False,       # Whether to include free-to-play worlds when checking latency
    "show_pvp_worlds": True         # Whether to include PVP and bounty hunter worlds when checking latency (*includes all four worlds on the pvp/bh world rota)
}


members_world_numbers = [
    2, 3, 4, 5, 6, 7, 9,
    10, 11, 12, 13, 14, 15, 17, 18, 19,
    20, 21, 22, 23, 24, 27, 28, 29,
    30, 31, 32, 33, 34, 36, 38, 39,
    40, 41, 42, 43, 44, 46, 47, 48, 49,
    50, 51, 52, 53, 54, 55, 56, 57, 58, 59,
    60, 61, 62, 65, 66, 67, 68, 69,
    70, 73, 74, 75, 76, 77, 78,
    86, 87, 88, 89,
    90, 91, 95, 96,
    116, 120, 121, 122
]

ftp_world_numbers = [
    1, 8, 16, 26, 35, 81, 82, 83, 84, 85, 93, 94, 117, 118, 119, 124
]

pvp_world_numbers = [
    18, 19, 24, 25, 37, 62, 71, 92
]


# Returns the combination of all world lists
#
# returns: list containing ALL worlds (mem + ftp + pvp)
def get_world_list_union():
    return list(set(members_world_numbers) | set(ftp_world_numbers) | set(pvp_world_numbers))


# Prefixes the numerical world used in the ping url with a 3 or 4 to match OSRS formatting
#   -world: a world number without the prefix '3' or '4', or that is shorter than three characters (ie. 32 or 116)
#
# returns: a formatted world number with the appropriate length and prefix (ie. 332 or 416)
def format_world(world):
    world_number = int(world)
    if world_number < 10:
        return "30" + str(world_number)
    elif world_number < 100:
        return "3" + str(world_number)
    else:
        return "4" + str(world_number)[1:]


# Converts a formatted world (ie. 312 or 422) back to the numerical value used in the ping url
#   -formatted_world: a formatted world number with the appropriate length and prefix (ie. 332 or 416)
#
# returns: a world INTEGER without the prefix '3' or '4', or that is shorter than three characters (ie. 32 or 116)
def deformat_world(formatted_world):
    world_str = str(formatted_world)
    if world_str[0] == '4':
        return int("1" + world_str[1:])
    elif world_str[0] == '3' and world_str[1] == '0':
        return int(world_str[2])
    elif world_str[0] == '3' and len(world_str) == 3:
        return int(world_str[1:])
    else:
        return int(world_str)


# Determines whether the string provided is a valid world
#   -world: a formatted or unformatted world number
#
# returns: true if the world is a valid digit and exists in one of the three explicitly defined world lists above
def is_valid_world(world):
    world_str = str(world)
    if not world_str.isdigit():
        return False

    if world_str[0] == '3' or world_str == '4':
        world_str = deformat_world(world_str)

    if not int(world_str) in get_world_list_union():
        return False

    return True


# Calls windows system ping cmdlet in a subprocess and returns the response when complete
#   -world: a world number without the prefix '3' or '4', or that is shorter than three characters (ie. 32 or 116)
#
# returns: a byte encoded response with latency data
def ping_server(world):
    process = subprocess.Popen(["ping.exe", "-n", str(options["ping_count"]), "oldschool" + str(world) + ".runescape.com"], stdout=subprocess.PIPE)
    return process.communicate()[0]


# Extracts desired ping values from the byte encoded response from #ping_server
#   -response: a byte encoded response with latency data
#
# returns: a dictionary of latency values (average, low, and high)
def parse_response(response):
    response_string = response.decode("utf-8")
    avg_ping = response_string.split("Average = ")[1].split("m")[0]
    min_avg_ping = response_string.split("Minimum = ")[1].split("m")[0]
    max_avg_ping = response_string.split("Maximum = ")[1].split("m")[0]
    return {
        "avg_ping": int(avg_ping),
        "low_ping": int(min_avg_ping),
        "high_ping": int(max_avg_ping)
    }


# Fetch the ping data for the specified world and pipe it back to the parent process
#   -world: a world number without the prefix '3' or '4', or that is shorter than three characters (ie. 32 or 116)
#   -pipe: a multiprocessing.Pipe that connects this process to the parent process
def get_ping(world, pipe):
    response = ping_server(world)
    ping = parse_response(response)
    pipe.send([str(world), ping])


# Print nicely formatted ping results
#   -world_title: a descriptor for the category of world numbers being processed (ie. Members, PVP, etc)
#   -avg_pings: a dictionary with world numbers as keys and average latency as values
#   -all_data: a dictionary with world numbers as keys and a child dictionary of latency information as values
#   -show_high_latency: whether the highest latency world should be diplayed in results
def print_results(world_title, avg_pings, all_data, show_high_latency):
    min_world = min(avg_pings, key=avg_pings.get)
    min_avg_ping = str(avg_pings[min_world])
    min_low_ping = str(all_data[min_world]["low_ping"])
    min_high_ping = str(all_data[min_world]["high_ping"])
    max_world = max(avg_pings, key=avg_pings.get)
    max_avg_ping = str(avg_pings[max_world])
    max_low_ping = str(all_data[max_world]["low_ping"])
    max_high_ping = str(all_data[max_world]["high_ping"])
    print("\n\n=============== " + world_title + " ===============")
    print("\n\t\tAvg\tMin\tMax")
    print("Lowest (W" + format_world(min_world) + "):\t" + min_avg_ping + "ms\t" + min_low_ping + "ms\t" + min_high_ping + "ms")
    if show_high_latency and options["show_high_latency"]:
        print("Highest (W" + format_world(max_world) + "):\t" + max_avg_ping + "ms\t" + max_low_ping + "ms\t" + max_high_ping + "ms")

    for i in range(len("=============== " + world_title + " ===============")):
        print("=", end='', flush=True)

    print("\n\n")


# Fetch and display latency data with the specified title for the given world numbers
#   -world_title: a descriptor for the category of world numbers being processed (ie. Members, PVP, etc)
#   -world_numbers: a list of DEFORMATTED world numbers to gather latency data from
def collect_ping_data(world_title, world_numbers):
    avg_pings = {}
    all_data = {}
    parent_pipe, child_pipe = multiprocessing.Pipe()
    j = 1
    k = 1

    print("Gathering latency data from worlds:")
    for i in range(len(world_numbers)):
        p = multiprocessing.Process(target=get_ping, args=(world_numbers[i], child_pipe,))
        p.start()

        # Sleep after executing a specified number of requests
        if j % options["bucket_size"] == 0:
            j = 0
            time.sleep(int(options["overlap_delay"]))
        j += 1

        print("W" + format_world(world_numbers[i]), end=' ', flush=True)

        # Display worlds currently being fetched
        if k % options["world_list_disp_cutoff"] == 0:
            print("", flush=True)
        k += 1

    print("\n\nWaiting for response" + ("s", "")[len(world_numbers) == 1] + "...")

    # Gather ping information child processes via pipes until information for all worlds has been collected
    while len(avg_pings) != len(world_numbers):
        child_response = parent_pipe.recv()
        avg_pings[child_response[0]] = child_response[1]["avg_ping"]
        all_data[child_response[0]] = child_response[1]

    print_results(world_title, avg_pings, all_data, len(world_numbers) != 1)


def main():
    if len(sys.argv) == 1:
        if options["show_members_worlds"]:
            collect_ping_data("Members' Worlds", members_world_numbers)

        if options["show_ftp_worlds"]:
            collect_ping_data("FTP Worlds", ftp_world_numbers)

        if options["show_pvp_worlds"]:
            collect_ping_data("PVP & BH Worlds", pvp_world_numbers)
    elif len(sys.argv) == 2:
        arg = sys.argv[1]
        if is_valid_world(arg):
            collect_ping_data("World " + arg, [deformat_world(arg)])
        else:
            print("The argument given is not a valid world")
            print("(Keep in mind DMM, tournament, or other seasonal worlds are not considered valid)")
            exit(1)

    exit(0)


# Application entry point
if __name__ == "__main__":
    main()