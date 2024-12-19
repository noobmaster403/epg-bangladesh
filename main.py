import requests
import json
from xml.etree.ElementTree import Element, SubElement, tostring
from datetime import datetime, timedelta
import pytz

# Function to format timestamp with timezone adjustment
def format_timestamp(timestamp):
    """Format Unix timestamp to the EPG-compatible format."""
    try:
        dt = datetime.fromtimestamp(int(timestamp), pytz.utc)  # Convert to UTC first
        bangladesh_tz = pytz.timezone('Asia/Dhaka')
        local_time = dt.astimezone(bangladesh_tz)
        return local_time.strftime('%Y%m%d%H%M%S') + ' +0600'  # Bangladesh timezone
    except ValueError:
        return ''

# Function to validate program times
def validate_program_times(start, end):
    """Validate program start and end times."""
    try:
        start_time = int(start)
        end_time = int(end)
        return start_time > 0 and end_time > start_time
    except ValueError:
        return False

# Function to generate API URLs for the next 3 days
def get_api_urls():
    """Generate API URLs for the next 3 days."""
    base_url = "https://cloudtv.akamaized.net/AynaOTT/BDcontent/channels/epg/652fcf82a2649538da6fc6e3_{}_minified_bundle.json"
    urls = []
    
    for i in range(3):  # For 3 days
        date = datetime.now() + timedelta(days=i)
        formatted_date = date.strftime("%d-%m-%Y")
        urls.append(base_url.format(formatted_date))
    
    return urls

# Function to fetch channel info
def get_channel_info():
    """Fetch channel information from the API."""
    try:
        response = requests.get("https://ayna-api.buddyxiptv.com/api/aynaott.json")
        response.raise_for_status()
        data = response.json()
        
        # Create a dictionary with channel_id as key
        channels_dict = {}
        for channel in data.get("channels", []):
            channels_dict[channel["id"]] = {
                "name": channel["name"],
                "category": channel["categoryName"],
                "logo": channel["logo"]
            }
        return channels_dict
    except Exception as e:
        print(f"Failed to fetch channel info: {e}")
        return {}

# Main script to create XML
try:
    # Get channel information first
    channel_info = get_channel_info()
    
    # Create XML structure
    tv = Element("tv")
    tv.set("generator-info-name", "Bangladesh EPG Generator")
    tv.set("generator-info-url", "")
    
    # Track channels to avoid duplicates
    processed_channels = set()
    
    # Fetch data for each day
    for api_url in get_api_urls():
        try:
            response = requests.get(api_url)
            response.raise_for_status()
            data = response.json()
            
            for channel in data:
                channel_id = channel.get("i", "unknown_id")
                channel_name = channel.get("n", "unknown_name")

                # Add channel only once with enhanced information
                if channel_id not in processed_channels:
                    channel_element = SubElement(tv, "channel", id=channel_id)
                    
                    # Add channel information from JSON if available
                    if channel_id in channel_info:
                        display_name = SubElement(channel_element, "display-name")
                        display_name.text = channel_info[channel_id]["name"]
                        
                        category = SubElement(channel_element, "category")
                        category.text = channel_info[channel_id]["category"]
                        
                        icon = SubElement(channel_element, "icon", src=channel_info[channel_id]["logo"])
                    else:
                        display_name = SubElement(channel_element, "display-name")
                        display_name.text = channel_name
                    
                    processed_channels.add(channel_id)

                # Sort programs by start time
                programs = channel.get("epg", [])
                programs.sort(key=lambda x: int(x.get("s", 0)))

                # Add EPG data
                for program in programs:
                    program_start = program.get("s", 0)
                    program_end = program.get("e", 0)

                    if not validate_program_times(program_start, program_end):
                        continue

                    program_name = program.get("n", "Unknown Program")
                    program_desc = program.get("d", "No description available")

                    start_time = format_timestamp(program_start)
                    end_time = format_timestamp(program_end)

                    if start_time and end_time:
                        program_element = SubElement(
                            tv, "programme",
                            start=start_time,
                            stop=end_time,
                            channel=channel_id
                        )
                        
                        title = SubElement(program_element, "title", lang="bn")
                        title.text = program_name
                        
                        desc = SubElement(program_element, "desc", lang="bn")
                        desc.text = program_desc

        except requests.exceptions.RequestException as e:
            print(f"Failed to fetch data for {api_url}: {e}")
            continue

    # Pretty print XML
    from xml.dom import minidom
    xml_str = minidom.parseString(tostring(tv, encoding="utf-8")).toprettyxml(indent="  ")
    
    # Save to file
    xml_file = "epg.xml"
    with open(xml_file, "w", encoding="utf-8") as f:
        f.write(xml_str)

    print(f"EPG has been successfully saved to {xml_file}!")

except Exception as ex:
    print(f"An error occurred: {ex}")
