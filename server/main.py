import datetime
import logging
import os
import pickle
import subprocess
import math
import uuid

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

logging.basicConfig(level=logging.DEBUG)
ffmpeg_path = "put_ffmpeg_exe_file_inside_here\\ffmpeg.exe"
movies_base_folder_path = 'D:\\Movies'
generated_files_path = "generated"

app = FastAPI()

# API routes
@app.get("/api/search/{search}")
def test_search2(search: str):
    results = []
    for item in subtitle_index_cache:
        for subtitle_items in item["subtitle_items"]:
            for subtitle_item in subtitle_items:
                for line in subtitle_item["text_lines"]:
                    lower_line = line.lower()
                    lower_search = search.lower()
                    if lower_search in lower_line:
                        temp = {}
                        temp["index_point"] = subtitle_item["index_point"]
                        temp["timestamp_text_start"] = subtitle_item["timestamp_text_start"]
                        temp["timestamp_text_end"] = subtitle_item["timestamp_text_end"]
                        temp["timestamp_start"] = subtitle_item["timestamp_start"]
                        temp["timestamp_end"] = subtitle_item["timestamp_end"]
                        temp["text_lines"] = subtitle_item["text_lines"]
                        temp["movie_file_name"] = item["movie_file_name"]
                        temp["movie_file_url"] = get_movie_url(item["movie_path"])
                        results.append(temp)

    return {
        "results": results
    }


@app.get("/api/find/{movieName}/{timestamp}")
def get_surrounding_subtitles(movieName: str, timestamp: str):
    # HH:MM:SS.mm (python is weird)
    timestamp_format = "%H:%M:%S,%f"
    timestamp_parsed = datetime.datetime.strptime(timestamp, timestamp_format).time()
    timestamp_milliseconds = get_milliseconds_from_time(timestamp_parsed)
    search_seconds = 10
    search_time_start_milliseconds = timestamp_milliseconds - (search_seconds * 1000)
    if search_time_start_milliseconds < 0:
        search_time_start_milliseconds = 0
    search_time_end_milliseconds = timestamp_milliseconds + (search_seconds * 1000)

    movie = None
    for item in subtitle_index_cache:
        if item["movie_file_name"] == movieName:
            movie = item
            break

    results = []
    for subtitle_item in movie["subtitle_items"][0]:
        if search_time_start_milliseconds < get_milliseconds_from_time(subtitle_item["timestamp_start"]) < search_time_end_milliseconds:
            subtitle_item["movie_file_name"] = item["movie_file_name"]
            subtitle_item["movie_file_url"] = get_movie_url(item["movie_path"])
            results.append(subtitle_item)

    return {
        "results": results
    }


@app.get("/api/video/{movieName}/{timestamp}")
def get_surrounding_video(movieName: str, timestamp: str):
    # HH:MM:SS.mm (python is weird)
    timestamp_format = "%H:%M:%S,%f"
    timestamp_parsed = datetime.datetime.strptime(timestamp, timestamp_format).time()
    timestamp_milliseconds = get_milliseconds_from_time(timestamp_parsed)
    search_seconds = 10
    search_time_start_milliseconds = timestamp_milliseconds - (search_seconds * 1000)
    if search_time_start_milliseconds < 0:
        search_time_start_milliseconds = 0
    search_time_end_milliseconds = timestamp_milliseconds + (search_seconds * 1000)

    movie = None
    for item in subtitle_index_cache:
        if item["movie_file_name"] == movieName:
            movie = item
            break

    timestamp_string_start = milliseconds_to_timestamp_string(search_time_start_milliseconds)
    timestamp_string_end = milliseconds_to_timestamp_string(search_time_end_milliseconds)
    new_guid = str(uuid.uuid4())
    new_movie_name = f"{new_guid}.mp4"
    new_subtitle_name = f"{new_guid}.vtt"

    transcode_video_file_part(movie["movie_path"], new_movie_name, timestamp_string_start, timestamp_string_end)
    transcode_subtitle_file_part(movieName, new_subtitle_name, timestamp, search_time_start_milliseconds)

    return {
        "new_movie_path": f"generated/{new_movie_name}",
        "new_subtitle_path": f"generated/{new_subtitle_name}",
    }


# Functions
def transcode_video_file_part(mkv_file_path, new_file_name, timestamp_string_start, timestamp_string_end):
    cmd_args = [ffmpeg_path, "-ss", timestamp_string_start, "-to", timestamp_string_end, "-i", mkv_file_path, "-c:v", "libx264", "-crf", "23", "-preset", "medium", "-c:a", "libvorbis", "-b:a", "128k", "-movflags", "+faststart", "-vf", "scale=-2:720,format=yuv420p", f"{generated_files_path}\\{new_file_name}"]
    out_from_console = subprocess.run(cmd_args, capture_output=True)
    return


def transcode_subtitle_file_part(movie_name, new_file_name, timestamp_string, start_at_milliseconds):
    subtitle_out = ["WEBVTT", ""]
    raw_in = get_surrounding_subtitles(movie_name, timestamp_string)

    # .sort(key=lambda i: i["timestamp_text_start"])
    for (index, item) in enumerate(raw_in["results"]):
        timestamp_start = milliseconds_to_timestamp_string(get_milliseconds_from_time(item['timestamp_start']) - start_at_milliseconds).replace(',','.')
        timestamp_end = milliseconds_to_timestamp_string(get_milliseconds_from_time(item['timestamp_end']) - start_at_milliseconds).replace(',','.')
        subtitle_out.append(f"{timestamp_start} --> {timestamp_end}")
        for l in item['text_lines']:
            subtitle_out.append(l)
        subtitle_out.append('')

    f = open(f"{generated_files_path}\\{new_file_name}", "a")
    f.write('\n'.join(subtitle_out))
    f.close()

    return


def milliseconds_to_timestamp_string(milliseconds_in):
    hours = math.floor(milliseconds_in / 1000 / 60 / 60)
    remainder = milliseconds_in - (hours * 1000 * 60 * 60)
    minutes = math.floor(remainder / 1000 / 60)
    remainder = milliseconds_in - (hours * 1000 * 60 * 60) - (minutes * 1000 * 60)
    seconds = math.floor(remainder / 1000)
    remainder = milliseconds_in - (hours * 1000 * 60 * 60) - (minutes * 1000 * 60) - (seconds * 1000)
    milliseconds = remainder
    return f"{str(hours).rjust(2, '0')}:{str(minutes).rjust(2, '0')}:{str(seconds).rjust(2, '0')}.{str(milliseconds).rjust(3, '0')}"


def get_movie_url(movie_path):
    return "/movies" + movie_path.replace(movies_base_folder_path, "").replace("\\", "/")


def get_milliseconds_from_time(time):
    return (time.hour * 60 * 60 * 1000) + (time.minute * 60 * 1000) + (time.second * 1000)


def get_subdirs(path):
    for (folder, sub_folders, files) in os.walk(path):
        return sub_folders


def get_files_in_all_subdirs(path):
    files_result = []
    for (folder, sub_folders, files) in os.walk(path):
        for file in files:
            files_result.append(f"{folder}\\{file}")

    return files_result


def return_movie_path_from_list(folder, files):
    movie_extensions = ['.mkv', '.mp4']
    for filename in files:
        for ext in movie_extensions:
            if ext in filename:
                return f'{folder}/{filename}'
    return None


def return_subtitle_path_from_list(folder, files):
    sub_extensions = ['.srt']
    for filename in files:
        for ext in sub_extensions:
            if ext in filename:
                return f'{folder}/{filename}'
    return None


def is_movie_file(file):
    movie_extensions = ['.mkv', '.mp4']
    for ext in movie_extensions:
        if file.endswith(ext):
            return True
    return False


def is_subtitle_file(file):
    language_list = ['eng']
    file_name = get_file_name_from_path(file)
    is_accepted_language = False
    for lang in language_list:
        if lang.lower() in file_name.lower():
            is_accepted_language = True

    if not is_accepted_language:
        return False

    subtitle_extensions = ['.srt']
    for ext in subtitle_extensions:
        if file.endswith(ext):
            return True
    return False


def get_path_of_file_without_file_name(file):
    lst = file.split("\\")
    lst.pop()
    return "\\".join(lst)


def get_file_name_from_path(file):
    lst = file.split("\\")
    return lst.pop()


def get_files_that_starts_with_path(path, all_files):
    res = []
    for file in all_files:
        if file.startswith(path):
                res.append(f"{file}")
    return res


def read_subtitle_file(file_path):
    file = open(file_path, "r", encoding='utf-8')
    lines = file.readlines()

    # HH:MM:SS.mm (python is weird)
    timestamp_format = "%H:%M:%S,%f"

    temp = {}
    result_list = []
    next_header_index = 0
    skip_lines = 0
    for (index, text) in enumerate(lines):
        if skip_lines > 0:
            skip_lines = skip_lines - 1
            continue

        if text == "\n":
            if "text_lines" not in temp or len(temp["text_lines"]) == 0:
                continue
            result_list.append(temp)
            next_header_index = index + 1
            continue

        if index == next_header_index:
            temp = {}
            temp["index_point"] = int(lines[index].replace("\n", ""))
            timestamp_split = lines[index+1].replace("\n", "").split(" --> ")
            temp["timestamp_text_start"] = timestamp_split[0]
            temp["timestamp_text_end"] = timestamp_split[1]
            temp["timestamp_start"] = datetime.datetime.strptime(temp["timestamp_text_start"], timestamp_format).time()
            temp["timestamp_end"] = datetime.datetime.strptime(temp["timestamp_text_end"], timestamp_format).time()
            temp["text_lines"] = []
            skip_lines = 1
            continue

        temp["text_lines"].append(text.replace("\n", ""))

    return result_list


def read_subtitle_from_mkv_file(file_path, track_id):
    subtitle_text = get_subtitle_text_from_mkv_file(file_path, track_id)
    subtitle_text = subtitle_text.replace("\r", "")
    lines = subtitle_text.split("\n")

    # HH:MM:SS.mm (python is weird)
    timestamp_format = "%H:%M:%S,%f"

    temp = {}
    result_list = []
    next_header_index = 0
    skip_lines = 0
    for (index, text) in enumerate(lines):
        if skip_lines > 0:
            skip_lines = skip_lines - 1
            continue

        if text.replace("\n", "") == "":
            if "text_lines" not in temp or len(temp["text_lines"]) == 0:
                continue
            result_list.append(temp)
            next_header_index = index + 1
            continue

        if index == next_header_index:
            temp = {}
            temp["index_point"] = int(lines[index].replace("\n", ""))
            timestamp_split = lines[index+1].replace("\n", "").split(" --> ")
            temp["timestamp_text_start"] = timestamp_split[0]
            temp["timestamp_text_end"] = timestamp_split[1]
            temp["timestamp_start"] = datetime.datetime.strptime(temp["timestamp_text_start"], timestamp_format).time()
            temp["timestamp_end"] = datetime.datetime.strptime(temp["timestamp_text_end"], timestamp_format).time()
            temp["text_lines"] = []
            skip_lines = 1
            continue

        temp["text_lines"].append(text.replace("\n", ""))

    return result_list


def get_subtitle_tracks_from_mkv_file(mkv_file_path):
    cmd_args = [ffmpeg_path, "-i", mkv_file_path, "-map", "0:s"]

    pipe = subprocess.Popen(cmd_args, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    res = pipe.communicate()
    error_response = res[1]

    metadata_raw_out = str(error_response).split("\\r\\n")
    subtitle_tracks_found = []
    pipe.kill()

    # Haha ffmpeg actually provides the track numbers, but they're wrong :D Nice trolling!
    subtitle_track_current_index = 0
    for line in metadata_raw_out:
        if "Stream #0:" in line and "Subtitle:" in line:
            if "(eng)" in line:
                subtitle_tracks_found.append(subtitle_track_current_index)
            subtitle_track_current_index = subtitle_track_current_index + 1

    return subtitle_tracks_found


def get_subtitle_text_from_mkv_file(mkv_file_path, subtitle_track_number):
    cmd_args = [ffmpeg_path, "-i", mkv_file_path, "-map", f"0:s:{subtitle_track_number}", "-f", "srt", "pipe:1"]

    pipe = subprocess.Popen(cmd_args, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    res = pipe.communicate()
    subtitle_text = res[0].decode("utf-8")
    pipe.kill()

    return subtitle_text


def create_subtitle_index():
    logging.info("create_subtitle_index starting... ")

    all_files = get_files_in_all_subdirs(movies_base_folder_path)
    subtitle_files = list(filter(is_subtitle_file, all_files))
    movie_files = list(filter(is_movie_file, all_files))

    results = []
    for movie in movie_files:
        movie_folder = get_path_of_file_without_file_name(movie)
        movie_file_name = get_file_name_from_path(movie)
        subtitle_files_in_folder = []
        if movie_folder != movies_base_folder_path:
            subtitle_files_in_folder = get_files_that_starts_with_path(movie_folder, subtitle_files)

        res = {
            "movie_path": movie,
            "movie_folder": movie_folder,
            "movie_file_name": movie_file_name,
            "subtitle_files_in_folder": subtitle_files_in_folder
        }
        logging.info("create_subtitle_index added movie file")
        results.append(res)

    for res in results:
        res["subtitle_items"] = []
        logging.info(f"create_subtitle_index reading movie: {res['movie_file_name']}")
        for file in res['subtitle_files_in_folder']:
            logging.info(f"create_subtitle_index reading subtitle: {file}")
            subtitle_track_object = read_subtitle_file(file)
            res["subtitle_items"].append(subtitle_track_object)

    for res2 in results:
        if not res2["movie_path"].endswith(".mkv"):
            continue
        subtitle_track_ids = get_subtitle_tracks_from_mkv_file(res2["movie_path"])
        res2["subtitle_items"] = []
        for track in subtitle_track_ids:
            logging.info(f"create_subtitle_index reading mkv track: {res2['movie_file_name']} {track}")
            subtitle_track_object = read_subtitle_from_mkv_file(res2["movie_path"], track)
            res2["subtitle_items"].append(subtitle_track_object)

    # Filter down to only the best subtitle for each movie (and only the movies that have subs)
    filtered_results = []
    for res3 in results:
        for index, sub in enumerate(res3["subtitle_items"]):
            if is_broken_subtitle(sub):
                del res3["subtitle_items"][index]

        if len(res3["subtitle_items"]) == 0:
            filtered_results = filtered_results + [res3]
            continue
        if len(res3["subtitle_items"]) == 1:
            filtered_results = filtered_results + [res3]
            continue
        best_subtitle = []
        for sub in res3["subtitle_items"]:
            if len(sub) > len(best_subtitle):
                best_subtitle = sub
        res3["subtitle_items"] = []
        res3["subtitle_items"].append(best_subtitle)
        filtered_results = filtered_results + [res3]

    return filtered_results


def is_broken_subtitle(subtitle_items):
    index = 0
    last_item = None
    insanity_count = 0
    while index < len(subtitle_items) - 1:
        index = index + 1
        if last_item is None:
            last_item = subtitle_items[index]
            continue
        if last_item["timestamp_text_start"] == subtitle_items[index]["timestamp_text_start"] and last_item["timestamp_text_end"] == subtitle_items[index]["timestamp_text_end"]:
            insanity_count = insanity_count + 1
        last_item = subtitle_items[index]
        if insanity_count > 10:
            return True
    return False


# INIT Sequence

# serve static files
app.mount("/generated", StaticFiles(directory=generated_files_path), name="generated")
app.mount("/movies", StaticFiles(directory=movies_base_folder_path), name="movies")
app.mount("/", StaticFiles(directory="../frontend/dist", html=True), name="static")



# load up the subtitle cache
subtitle_index_cache = None
try:
    pickle_off = open("subtitle_index_cache.pickle", 'rb')
    subtitle_index_cache = pickle.load(pickle_off)
except FileNotFoundError:
    subtitle_index_cache = None

if subtitle_index_cache is None:
    subtitle_index_cache = create_subtitle_index()
    pickling_on = open("subtitle_index_cache.pickle", "wb")
    pickle.dump(subtitle_index_cache, pickling_on)
    pickling_on.close()
