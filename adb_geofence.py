import asyncio
from asyncio.subprocess import PIPE
import subprocess
import re
from math import radians, cos, sin, sqrt, atan2


# GEOFENCE_LAT = 13.032247
# GEOFENCE_LON = 77.562837

GEOFENCE_LAT = 13.032247
GEOFENCE_LON = 77.562837

GEOFENCE_RADIUS = 500000  # in meters

def is_within_geofence(lat, lon):
    
    R = 6371000  # Radius of the Earth in meters
    lat1 = radians(GEOFENCE_LAT)
    lon1 = radians(GEOFENCE_LON)
    lat2 = radians(lat)
    lon2 = radians(lon)

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = sin(dlat / 2)*2 + cos(lat1) * cos(lat2) * sin(dlon / 2)*2
    a = max(0, min(a, 1))
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    distance = R * c

    return distance <= GEOFENCE_RADIUS




async def get_device_location(device_serial):
    try:
        output = subprocess.check_output(['adb', 'shell', 'dumpsys', 'location']).decode('utf-8')
    except subprocess.CalledProcessError as e:
        print("Error executing command:", e)
        exit()


    match = re.search(r'last\s+location', output)

    if match:
       
        latitude_match = re.search(r'[-+]?\d*\.\d+|\d+', output[match.end():])
        longitude_match = re.search(r'[-+]?\d*\.\d+|\d+', output[match.end() + latitude_match.end():])

        if latitude_match and longitude_match:
            latitude = float(latitude_match.group())
            longitude = float(longitude_match.group())

            print("Latitude:", latitude)
            print("Longitude:", longitude)
            return latitude,longitude
        else:
            print("Latitude and/or longitude not found.")
    else:
        print("Last known location not found.")
    return None,None

async def get_foreground_app(device_serial):
    try:
        process = await asyncio.create_subprocess_exec(
            'adb', '-s', device_serial, 'shell', 'dumpsys', 'activity', 'activities',
            stdout=PIPE, stderr=PIPE
        )
        stdout, stderr = await process.communicate()

        output = stdout.decode('utf-8')

       
        for line in output.split('\n'):
            if 'mResumedActivity' in line:
                
                print(line)
                
                package_name = line.split()[3].split('/')[0]
                return package_name
    except Exception as e:
        print(f"Error: {e}")
    return None

async def block_app(device_serial, package_name):
    if package_name in ['com.whatsapp', 'com.google.android.youtube']:
        try:
            process = await asyncio.create_subprocess_exec(
                'adb', '-s', device_serial, 'shell', 'am', 'force-stop', package_name,
                stdout=PIPE, stderr=PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                print(f"Blocked app: {package_name}")
            else:
                print(f"Error: {stderr.decode('utf-8')}")
        except Exception as e:
            print(f"Error: {e}")

async def main():


    process = await asyncio.create_subprocess_exec(
        'adb', 'devices',
        stdout=PIPE, stderr=PIPE
    )
    stdout, stderr = await process.communicate()
    output = stdout.decode('utf-8')

  
    devices = []
    for line in output.split('\n')[1:]:
        if '\tdevice' in line:
            devices.append(line.split('\t')[0])

    if not devices:
        print("No devices found")
        return


    tasks = []
    for device_serial in devices:
        lat, lon = await get_device_location(device_serial)
        if lat is not None and lon is not None:
            if is_within_geofence(lat, lon):
                foreground_app = await get_foreground_app(device_serial)
                print(f"The foreground app for device {device_serial} is: {foreground_app}")

                
                if foreground_app:
                    tasks.append(block_app(device_serial, foreground_app))
            else:
                print(f"Device {device_serial} is outside the geofence.")
        else:
            print(f"Could not get location for device {device_serial}")

    
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    while True:
        asyncio.run(main())