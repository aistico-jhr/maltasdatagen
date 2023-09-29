import random
from datetime import datetime, timedelta, time
from pytz import timezone, UTC
from sys import argv

ROLE_NOT_SELECTED = 0
ROLE_NURSE = 1
ROLE_PHYSICIAN = 2

MAX_PAUSES = 4
MAX_PAUSE_DURATION = 30

def _print_header():
    print("measurement_id;device_id;role_id;start_time_iso;end_time_iso;total_time_spent;status")

def _print_record(measurement_id, device_id, role_id, start_time, end_time, total_time_spent, status):
    # Print in ISO format without sub-seconds and append 'Z'
    start_time_iso = start_time.astimezone(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')
    end_time_iso = end_time.astimezone(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')
    print(f"{measurement_id};{device_id};{role_id};{start_time_iso};{end_time_iso};{total_time_spent};{status}")


def start_and_complete(start_time, device_id, measurement_id, role_id):
    total_time_spent = 0
    _print_record(measurement_id, device_id, role_id, start_time, start_time, total_time_spent, 'STARTED')

    total_time_spent = random.randint(180, 190)
    end_time = start_time + timedelta(seconds=total_time_spent)
    _print_record(measurement_id, device_id, role_id, start_time, end_time, total_time_spent, 'COMPLETE')
    
    return (end_time, measurement_id)

def _start_with_pauses(start_time, device_id, measurement_id, role_id, complete=True, can_return=True):
    will_restart = False
    total_time_spent = 0
    _print_record(measurement_id, device_id, role_id, start_time, start_time, total_time_spent, 'STARTED')

    status = 'STARTED'
    pause_count = random.randint(0, MAX_PAUSES)
    for i in range(pause_count): 

        if status == 'PAUSED':
            pause_duration = random.randint(5, MAX_PAUSE_DURATION+5)
            # Was away for too long, Interrupt and come back to start again.
            if pause_duration > MAX_PAUSE_DURATION and can_return:
                will_restart = True
                break # The pause count
            # If could not return, this can be over MAX_PAUSE_DURATION, normalize it
            pause_duration = min(pause_duration, MAX_PAUSE_DURATION)

            end_time = start_time + timedelta(seconds=pause_duration)
            _print_record(measurement_id, device_id, role_id, start_time, end_time, total_time_spent, 'CONTINUED')
            start_time = end_time
            status == 'CONTINUED'
        
        last_pause = i+1==pause_count
        if will_restart or not last_pause or (last_pause and not complete):
            # Measure for some time, then pause
            measure_duration = max(5, random.randint(0, 160-pause_count*((160-20)/MAX_PAUSES)))
            while total_time_spent+measure_duration>180:
                measure_duration = measure_duration/2
            total_time_spent+=measure_duration
            end_time = start_time + timedelta(seconds=measure_duration)
            _print_record(measurement_id, device_id, role_id, start_time, end_time, total_time_spent, 'PAUSED')
            start_time = end_time
            status = 'PAUSED'
    
    if status=='PAUSED':
        # User leaves early (interrupts)
        away_duration = MAX_PAUSE_DURATION
        end_time = start_time + timedelta(seconds=away_duration)
        _print_record(measurement_id, device_id, role_id, start_time, end_time, total_time_spent, 'INTERRUPTED')
    else:
        last_measure_duration = 180-total_time_spent+random.randint(0, 10)
        total_time_spent += last_measure_duration
        end_time = start_time + timedelta(seconds=last_measure_duration)
        _print_record(measurement_id, device_id, role_id, start_time, end_time, total_time_spent, 'COMPLETE')

    if will_restart:
        will_complete_p = random.random()
        measurement_id+=1
        if will_complete_p<0.3:
            return start_and_complete(end_time, device_id, measurement_id, role_id)
        elif complete:
            return _start_with_pauses(start_time, device_id, measurement_id, role_id, complete=True, can_return=False)
        else:
            return _start_with_pauses(start_time, device_id, measurement_id, role_id, complete=False, can_return=False)

    return (end_time, measurement_id)

def start_pause_continue_complete(start_time, device_id, measurement_id, role_id):
    return _start_with_pauses(start_time, device_id, measurement_id, role_id, complete=True)

def start_pause_continue_interrupt(start_time, device_id, measurement_id, role_id):
    return _start_with_pauses(start_time, device_id, measurement_id, role_id, complete=False)

def simulate_from(start_date, end_date, functions_with_probabilties, staff_min, staff_max, device_id):
    
    # Parameters
    start_time = time(8, 0)
    end_time = time(20, 0)
    mean_surgery_time = 120  # in minutes
    stddev_surgery_time = 30  # in minutes
    mean_prep_cleanup_time = 30  # in minutes
    stddev_prep_cleanup_time = 15  # in minutes
    working_days = set([0, 1, 2, 3, 4, 5])  # Monday=0, Sunday=6

    double_time_slot_prob = 0.5
    skip_time_slot_prob = 0.33

    # Initialize
    current_date = start_date

    measurement_id = 0

    _print_header()

    # Simulation for multiple months
    while current_date <= end_date:
        if current_date.weekday() in working_days:
            current_time = datetime.combine(current_date, start_time)
            end_of_day = datetime.combine(current_date, end_time)
            
            while True:
                if random.random()<double_time_slot_prob:
                    random_surgery_time = timedelta(minutes=random.gauss(mean_surgery_time*2, stddev_surgery_time*2))
                else:
                    random_surgery_time = timedelta(minutes=random.gauss(mean_surgery_time, stddev_surgery_time))
                random_prep_cleanup_time = timedelta(minutes=random.gauss(mean_prep_cleanup_time, stddev_prep_cleanup_time))

                if current_time + random_surgery_time + random_prep_cleanup_time <= end_of_day:
                    surgery_start = current_time
                    measurement_start = surgery_start
                    surgery_end = current_time + random_surgery_time
                    current_time = surgery_end + random_prep_cleanup_time

                    if random.random()<skip_time_slot_prob:
                        continue

                    staffc = random.randint(staff_min, staff_max)
                    roles = [0]*staffc

                    # Physician roles (1-3)
                    roles[-1] = 2 # Surgeon is always last :)
                    for _ in range(random.randint(1,2)):
                        random_index = random.randint(1, len(roles) - 1)
                        roles[random_index] = 2
                    for _ in range(random.randint(1,5)):
                        random_index = random.randint(0, len(roles) - 1)
                        if roles[random_index]==0:
                            roles[random_index] = 1

                    for role_id in roles:
                        measurement_type_p = random.random()
                        for p, f in functions_with_probabilties:
                            if measurement_type_p<p:
                                end_measurement_at, measurement_id = f(measurement_start, device_id, measurement_id, role_id)
                                measurement_id+=1
                                measurement_start = end_measurement_at + timedelta(seconds=random.randint(5, 360))
                                break
                    
                else:
                    break
                    
        current_date += timedelta(days=1)

if __name__=="__main__":
    probabilities = [
        (0.5, start_and_complete),
        (0.8, start_pause_continue_complete),
        (1.0, start_pause_continue_interrupt)
    ]
    
    did = 1
    if len(argv)>1:
        did = int(argv[1])

    finland_tz = timezone('Europe/Helsinki')
    start_from = datetime.now(finland_tz)
    end_to = start_from+timedelta(days=30)
    simulate_from(start_from, end_to, probabilities, 5, 8, device_id=did)
    




