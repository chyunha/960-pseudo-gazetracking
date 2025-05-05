#!/usr/bin/env python3  # Shebang for proper execution

from flask import Flask, render_template, request, jsonify
import csv, json, os
import logging

app = Flask(__name__)

# Set up basic logging for error tracking
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

IMAGE_SETS_FILE = 'stimuli_sets_id.csv' # set_id, prompt, image 1-40
ASSIGNMENT_LOG = 'assignment_log.json'
PARTICIPANTS_DIR = 'participants'
os.makedirs(PARTICIPANTS_DIR, exist_ok=True)

prompts = {
    "0": "Click continuously, everywhere you look.",
    "1": "Click continuously, everywhere you look. Focus your gaze on the most important parts of the image.",
    "2": "Click continuously, everywhere you look. Focus your gaze on what you find interesting about the image."
}

def load_image_sets():
    """
    Returns
        {0: {
            "prompt": 0,
            "img1": 2, ...
        },
        1: {...}}
    """
    sets_dict = {}
    with open(IMAGE_SETS_FILE, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            set_id = row['set_id']
            values = {id: prompt_imgs for id, prompt_imgs in row.items() if id != 'set_id'}
            sets_dict[set_id] = values
    return sets_dict


def log_assignment(participant_id, set_id):
    log_data = {}

    # load existing log if it exists
    if os.path.exists(ASSIGNMENT_LOG):
        with open(ASSIGNMENT_LOG, 'r') as f:
            try:
                log_data = json.load(f)
            except json.JSONDecodeError:
                raise ValueError("Assignment log file is corrupted or not valid JSON.")

    # throw error if image set has already been assigned
    if set_id in log_data.values():
        raise ValueError(f"Image set already assigned")
    
    # add or update participant's assignment
    log_data[participant_id] = set_id

    # save updated log
    with open(ASSIGNMENT_LOG, 'w') as f:
        json.dump(log_data, f, indent=2)


def get_unassigned_ids():
    all_set_ids = set(load_image_sets().keys())
    assigned_set_ids = set()
    if os.path.exists(ASSIGNMENT_LOG):
        with open(ASSIGNMENT_LOG, 'r') as f:
            try:
                assignment_log = json.load(f)
                assigned_set_ids = set(assignment_log.values())
            except json.JSONDecodeError:
                raise ValueError("Assignment log file is corrupted or not valid JSON.")
            
    unassigned_set_ids = all_set_ids - assigned_set_ids
    return sorted(unassigned_set_ids)


@app.route('/')
def start():
    image_set_dict = load_image_sets()

    # create list of unassigned sets
    unassigned_set = get_unassigned_ids()

    # if empty (failsafe)
    if not unassigned_set: 
        return "All image sets have been assigned. Experiment is full."
        # do i need to have some kind of break here...
    
    curr_set_assign = unassigned_set[0]
    participant_id = 1090 - len(unassigned_set) # assign random 4-digit id
    log_assignment(participant_id, curr_set_assign)

    # create subdirectory for each participant
    participant_path = os.path.join(PARTICIPANTS_DIR, participant_id)
    os.makedirs(participant_path, exist_ok=True)

    # with open(os.path.join(participant_path, "partipant_set_assignment.json"), 'w') as f:
    #     json.dump({
    #         "participannt_id": participant_id,
    #         "image_set": assigned_set
    #     }, f)

    return render_template("experiment.html", participant_id=participant_id, image_set=image_set_dict[curr_set_assign])

@app.route('/submit', methods=['POST'])
def submit():
    data = request.get_json()
    participant_id = data.get('participant_id')
    click_data = data.get('click_data')

    participant_path = os.path.join(PARTICIPANTS_DIR, participant_id)
    if not os.path.isdir(participant_path):
        return jsonify({"error": "Invalid participant ID"}), 400

    for image_name, clicks in click_data.items():
        file_path = os.path.join(participant_path, f"{image_name}.json")
        with open(file_path, 'w') as f:
            json.dump(clicks, f, indent=2)

    return jsonify({"status": "success"})

if __name__ == '__main__':
    app.run(debug=True)


