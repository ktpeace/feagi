
# Copyright 2016-2022 The FEAGI Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================

"""
Burst engine is responsible for the event driven behavior of the artificial brain. It facilitates the firing all the
contents of the Fire Candidate List (FCL) at the same instant.

todo: Engine modes; one the super mode used for automated training and evaluations, second one with the speed of life.
todo: figure how to calibrate the speed of engine with IPU feeder
todo: assess viability of having a GIL like behavior for burst engine
todo: implement autopilot mode suitable for automated training and testing vs speed of life
todo: need a higher level mechanism to switch between life mode and autopilot mode something like falling sleep
        - let the lack of IPU activity for a period to trigger the education mode. IPU activity to wake up in life mode
        - Question: Where does IPU activity monitor belong? Thalamus? IPU controller? FCL injector?
        - Solution: FCL Injector can keep track of IPU activities in a variable and set a flag accordingly
"""
import os
import glob
from datetime import datetime
from time import sleep
from npu.physiology import *
from npu import stimulator
from mem.memory import neuroplasticity
from evo.stats import *
from inf.initialize import init_burst_engine, exit_burst_process
from inf.messenger import Pub, Sub
from pns.pns_router import opu_router, stimuli_router
from api.message_processor import api_message_processor
from trn.trainer import shock_manager


def cortical_group_members(group):
    # members = []
    # for item in runtime_data.cortical_list:
    #     if runtime_data.genome['blueprint'][item]['group_id'] == group:
    #         members.append(item)
    return [item for item in runtime_data.cortical_list if runtime_data.genome['blueprint'][item]['group_id'][:1]
            == group]


def burst_manager():
    """This function behaves as instance of Neuronal activities"""

    def burst_duration_calculator(controller_capabilities):
        """
        Analyzes controller capabilities and sets the burst duration in a way to support the fastest device
        """
        # todo: look into more dynamic mechanisms to set the burst duration timer
        # using the burst_timer as the starting point
        lowest_refresh_rate = runtime_data.burst_timer
        if controller_capabilities:
            for device in controller_capabilities:
                if "refresh_rate" in device:
                    if device["refresh_rate"] < lowest_refresh_rate:
                        lowest_refresh_rate = device["refresh_rate"]
            return float(lowest_refresh_rate)
        else:
            return runtime_data.burst_timer

    def consciousness_manager():
        """responsible for start and stop of all non-main threads based on various conditions"""
        # Check flags for IPU activities
        # todo: need mechanism to set the ipu_idle flag if there is no IPU activity for a period
        # Alert condition checks to ensure brain is not in Alert mode which can be triggered via fear or cautiousness
        elapsed_time = datetime.now() - runtime_data.last_alertness_trigger
        alert_condition = elapsed_time.seconds > int(runtime_data.parameters['Timers']['alert_mode_duration'])
        if alert_condition:
            time_delta = datetime.now() - runtime_data.last_ipu_activity
            if time_delta.seconds > int(runtime_data.genome['ipu_idle_threshold']):
                # Go to sleep by stopping IPU/OPU threads
                # todo: instead of turning off the IPU, reduce IPU responsiveness so via an trigger brain can awake
                print(">> >> Brain going to sleep..")

                # todo: adjust burst frequency

        # todo: implementation of coming out of sleep
        # one trigger to be large activity on IPU and another to be time-bound
        ready_to_wake = False
        if ready_to_wake:
            print(">> >> Brain waking up from sleep..")

            # todo: adjust burst frequency

    def init_fcl(cortical_area_):
        runtime_data.fire_candidate_list[cortical_area_] = set()
        runtime_data.future_fcl[cortical_area_] = set()
        runtime_data.previous_fcl[cortical_area_] = set()
        # runtime_data.upstream_neurons[cortical_area_] = {}

    def capture_cortical_activity_stats():
        # print('@@@--- Activity Stats:', runtime_data.activity_stats)
        for cortical_area_ in runtime_data.fire_candidate_list:
            if cortical_area_ not in runtime_data.activity_stats:
                runtime_data.activity_stats[cortical_area_] = len(runtime_data.fire_candidate_list[cortical_area_])

            cortical_neuron_count = len(runtime_data.fire_candidate_list[cortical_area_])
            runtime_data.activity_stats[cortical_area_] = \
                max(runtime_data.activity_stats[cortical_area_], cortical_neuron_count)

            if (runtime_data.parameters["Database"]["influxdb_enabled"] and
                    runtime_data.influxdb and
                    runtime_data.parameters["Database"]["influx_stat_logger"]):
                runtime_data.influxdb.insert_burst_activity(
                    connectome_path=runtime_data.parameters['InitData']['connectome_path'],
                    burst_id=runtime_data.burst_count,
                    cortical_area=cortical_area_,
                    neuron_count=cortical_neuron_count)

            if runtime_data.parameters["Switches"]["global_logger"] and \
                    runtime_data.parameters["Logs"]["print_cortical_activity_counters"]:
                if cortical_neuron_count > 0:
                    print(settings.Bcolors.RED + '    %s : %i/%i %s  '
                          % (cortical_area_, cortical_neuron_count,
                             runtime_data.genome['blueprint'][cortical_area_]['per_voxel_neuron_cnt'] *
                             runtime_data.genome['blueprint'][cortical_area_]["neuron_params"]['block_boundaries'][0] *
                             runtime_data.genome['blueprint'][cortical_area_]["neuron_params"]['block_boundaries'][1] *
                             runtime_data.genome['blueprint'][cortical_area_]["neuron_params"]['block_boundaries'][2]
                             , active_neurons_in_blocks(cortical_area_)) + settings.Bcolors.ENDC)
                elif runtime_data.parameters["Logs"]["print_cortical_activity_counters_all"]:
                    print(settings.Bcolors.YELLOW + '    %s : %i  '
                          % (cortical_area_, cortical_neuron_count)
                          + settings.Bcolors.ENDC)

    def burst_stats(burst_start_time):
        if runtime_data.parameters["Logs"]["print_burst_stats"]:
            for area in runtime_data.brain:
                print("### Average postSynaptic current in --- %s --- was: %i"
                      % (area, average_postsynaptic_current(area)))

        if runtime_data.parameters["Logs"]["print_upstream_neuron_stats"]:
            # Listing the number of neurons activating each UTF memory neuron
            upstream_report_time = datetime.now()
            upstream_general_stats, upstream_fcl_stats = \
                list_upstream_neuron_count_for_digits(mode=1)
            print("list_upstream_neuron_count_for_digits:", upstream_general_stats)
            print("list_upstream___FCL__count_for_digits:", upstream_fcl_stats)

            print("Timing : Upstream + common neuron report:", datetime.now() - upstream_report_time)

        burst_duration = datetime.now() - burst_start_time
        if runtime_data.parameters["Logs"]["print_burst_info"]:
            if runtime_data.genome_ver == "2.0":
                print(settings.Bcolors.UPDATE +
                      ">>> Burst duration: %s %i --- ---- ---- ---- ---- ---- ----"
                      % (burst_duration, runtime_data.burst_count) + settings.Bcolors.ENDC)
            else:
                print(settings.Bcolors.YELLOW +
                      ">>> Burst duration: %s %i --- ---- ---- ---- ---- ---- ----"
                      % (burst_duration, runtime_data.burst_count) + settings.Bcolors.ENDC)

    def evolutionary_checkpoint():
        if runtime_data.burst_count % runtime_data.genome['evolution_burst_count'] == 0:
            print('Evolution phase reached...')
            for area in runtime_data.cortical_list:
                neuron_count, synapse_count = connectome_total_synapse_cnt(area)
                if (runtime_data.parameters["Database"]["influxdb_enabled"] and 
                        runtime_data.influxdb and 
                        runtime_data.parameters["Database"]["influx_stat_logger"]):
                    runtime_data.influxdb.insert_connectome_stats(connectome_path=connectome_path,
                                                     cortical_area=area,
                                                     neuron_count=neuron_count,
                                                     synapse_count=synapse_count)
            # genethesizer.generation_assessment()

    def refractory_check(cortical_area, neuron_id):
        # Refractory period check
        # consider case where last_burst_num = 0 when doing refractory period check
        # TODO: incorporate (or at least consider) this last_burst_num check in function refactor
        dst_neuron_obj = runtime_data.brain[cortical_area][neuron_id]
        if dst_neuron_obj["last_burst_num"] > 0:
            if dst_neuron_obj["last_burst_num"] + \
                    runtime_data.genome["blueprint"][cortical_area]["neuron_params"]["refractory_period"] <= \
                    runtime_data.burst_count:
                # Inhibitory effect check
                if dst_neuron_obj["snooze_till_burst_num"] <= runtime_data.burst_count:
                    # Adding neuron to fire candidate list for firing in the next round
                    return True
                else:
                    return False
        else:
            if dst_neuron_obj["snooze_till_burst_num"] <= runtime_data.burst_count:
                return True
            else:
                return False

    def consecutive_fire_threshold_check(cortical_area, neuron_id):
        # Condition to snooze the neuron if consecutive fire count reaches threshold
        if runtime_data.brain[cortical_area][neuron_id]["consecutive_fire_cnt"] > \
                runtime_data.genome["blueprint"][cortical_area]["neuron_params"]["consecutive_fire_cnt_max"]:
            snooze_till(cortical_area, neuron_id, runtime_data.burst_count +
                        runtime_data.genome["blueprint"][cortical_area]["neuron_params"]["snooze_length"])
            return False
        else:
            return True

    def fire_fcl_contents():
        # time_firing_activities = datetime.now()

        if candidate_list_counter(runtime_data.fire_candidate_list) == 0:
            runtime_data.empty_fcl_counter += 1
            print("FCL is empty!")
        else:
            # Capture cortical activity stats
            capture_cortical_activity_stats()
            # Develop a final neuron fire queue based on all the neuron membrane potential fluctuations

            # fire_queue holds a temporary list of neurons updated during a single burst to determine which to fire
            runtime_data.fire_queue = dict()

            # Fire FCL neurons and pre-process viability of the downstream neurons for firing
            for _ in runtime_data.fire_candidate_list:
                if "degeneration" not in runtime_data.genome['blueprint'][_] or \
                        runtime_data.genome['blueprint'][_]['degeneration'] is None:
                    degeneration_val = 0
                else:
                    degeneration_val = runtime_data.genome['blueprint'][_]['degeneration']
                while runtime_data.fire_candidate_list[_]:
                    neuron_to_fire = runtime_data.fire_candidate_list[_].pop()
                    neuron_pre_fire_processing(_, neuron_to_fire, degenerate=degeneration_val)

            # Add neurons to future FCL
            for cortical_area in runtime_data.fire_queue:
                for neuron_id in runtime_data.fire_queue[cortical_area]:
                    leak_amount = neuron_leak(cortical_area=cortical_area, neuron_id=neuron_id)
                    membrane_potential = runtime_data.fire_queue[cortical_area][neuron_id][0] - leak_amount
                    fire_threshold = runtime_data.fire_queue[cortical_area][neuron_id][1]

                    # When neuron is ready to fire
                    if membrane_potential > fire_threshold and \
                            refractory_check(cortical_area, neuron_id) and \
                            consecutive_fire_threshold_check(cortical_area, neuron_id):
                        # The actual trigger to fire the neuron
                        runtime_data.brain[cortical_area][neuron_id]["last_membrane_potential_reset_burst"] = \
                            runtime_data.burst_count
                        # Setting the membrane potential of the neuron to 0 after being added to fire list
                        membrane_potential_update(cortical_area=cortical_area, neuron_id=neuron_id,
                                                  membrane_potential_change=0, overwrite=True,
                                                  overwrite_value=0)
                        runtime_data.future_fcl[cortical_area].add(neuron_id)

                    elif membrane_potential < 0:
                        # Setting the membrane potential of the neuron to 0 as the least allowable mp level
                        membrane_potential_update(cortical_area=cortical_area, neuron_id=neuron_id,
                                                  membrane_potential_change=0, overwrite=True,
                                                  overwrite_value=0)

                    else:
                        runtime_data.brain[cortical_area][neuron_id]["residual_membrane_potential"] = membrane_potential
                        membrane_potential_update(cortical_area=cortical_area, neuron_id=neuron_id,
                                                  membrane_potential_change=0, overwrite=True,
                                                  overwrite_value=membrane_potential)

            # Transferring future_fcl to current one and resetting the future one in process
            for _ in runtime_data.future_fcl:
                runtime_data.fire_candidate_list[_] = \
                    set([item for item in runtime_data.future_fcl[_]])
                runtime_data.future_fcl[_] = set()

    def log_burst_activity_influx():
        if (runtime_data.parameters["Database"]["influxdb_enabled"] and 
                runtime_data.influxdb and 
                runtime_data.parameters["Database"]["influx_stat_logger"]):
            runtime_data.influxdb.insert_burst_checkpoints(connectome_path, runtime_data.burst_count)

    def init_burst_pub():
        # Initialize a broadcaster
        burst_engine_pub_address = 'tcp://0.0.0.0:' + runtime_data.parameters['Sockets']['feagi_outbound_port']
        runtime_data.burst_publisher = Pub(address=burst_engine_pub_address)
        print("Burst publisher has been initialized @ ", burst_engine_pub_address)

    def controller_handshake():
        broadcast_message = {}
        broadcast_message['burst_counter'] = runtime_data.burst_count
        # broadcast_message['sockets'] = runtime_data.parameters['Sockets']
        broadcast_message['burst_frequency'] = runtime_data.burst_timer
        broadcast_message['godot'] = runtime_data.burst_activities
        broadcast_message['opu_data'] = runtime_data.opu_data
        broadcast_message['genome_num'] = runtime_data.genome_counter
        # broadcast_message['cortical_dimensions'] = runtime_data.cortical_dimensions

        runtime_data.burst_publisher.send(message=broadcast_message)
        runtime_data.opu_data = {}

    def message_router():
        # IPU listener: Receives IPU data through ZMQ channel
        if runtime_data.router_address_gazebo is not None:
            gazebo_data = gazebo_listener.receive()
            # Dynamically adjusting burst duration based on Controller needs
            runtime_data.burst_timer = burst_duration_calculator(gazebo_data)
            if gazebo_data:
                stimuli_router(gazebo_data)

        # IPU listener: Receives IPU data through ZMQ channel
        if runtime_data.router_address_godot is not None:
            godot_data = godot_listener.receive()
            # Dynamically adjusting burst duration based on Controller needs
            runtime_data.burst_timer = burst_duration_calculator(godot_data)
            if godot_data:
                stimuli_router(godot_data)

        # IPU listener: Receives IPU data through REST API
        if runtime_data.stimulation_script is not None:
            virtual_data = stimulator.stimulate()
            if virtual_data:
                stimuli_router({"data": {"direct_stimulation": virtual_data}})

        # Evaluated multiple scenarios and administers shock as needed
        if runtime_data.shock_admin:
            shock_manager()

        # Broadcasts a TCP message on each burst
        if runtime_data.brain_activity_pub:
            # todo: Obtain the frequency from controller config
            if runtime_data.burst_count % runtime_data.brain_activity_pub_freq == 0:
                activity_data = brain_activity_voxelizer()
                runtime_data.burst_activities = activity_data

    def brain_activity_voxelizer():
        """
        Convert FCL activities to a set of voxel locations and sends out through the ZMQ publisher
        """
        broadcast_message = set()

        for _ in runtime_data.fire_candidate_list:
            fire_list = set(runtime_data.fire_candidate_list[_])
            if runtime_data.genome['blueprint'][_]['neuron_params'].get('visualization'):
                while fire_list:
                    firing_neuron = fire_list.pop()
                    firing_neuron_loc = runtime_data.brain[_][firing_neuron]['soma_location']
                    relative_coords = runtime_data.genome['blueprint'][_]['neuron_params'].get('relative_coordinate')
                    broadcast_message.add(
                        (
                            runtime_data.burst_count,
                            firing_neuron_loc[0] + relative_coords[0],
                            firing_neuron_loc[1] + relative_coords[1],
                            firing_neuron_loc[2] + relative_coords[2]
                        )
                    )
        return broadcast_message

    def terminate_on_low_perf():
        # TBD
        pass

    def burst():
        if runtime_data.new_genome:
            print("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            print("Burst engine has detected a new genome!")
            print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
            print("Cortical list", runtime_data.cortical_list)

            for area in runtime_data.cortical_list:
                init_fcl(area)
            runtime_data.new_genome = False

        if not runtime_data.api_queue:
            pass
        elif runtime_data.api_queue.empty():
            pass
        else:
            api_message = runtime_data.api_queue.get()
            api_message_processor(api_message)
            return

        if runtime_data.exit_condition:
            print("%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%\n"
                  "##   Exit Condition Triggered   ##\n"
                  "%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%")
            runtime_data.burst_publisher.terminate()
            godot_listener.terminate()
            gazebo_listener.terminate()
            return
        # todo: the following sleep value should be tied to Autopilot status
        sleep(float(runtime_data.burst_timer))

        runtime_data.neuron_leak_dict = {}

        burst_start_time = datetime.now()
        log_burst_activity_influx()
        runtime_data.pain_flag = False
        runtime_data.burst_count += 1

        # Manage ZMQ communication from and to FEAGI
        message_router()

        # Process efferent signals
        opu_router()

        # Feeding FCL queue content into the FCL
        while not runtime_data.fcl_queue.empty():
            fcl_tmp = runtime_data.fcl_queue.get()

            for _ in fcl_tmp:
                runtime_data.fire_candidate_list[_] = \
                    set([item for item in fcl_tmp[_]])
                fcl_tmp = set()

        # print("^^^^^^^^^^ Current FCL ^^^^^^^^^\n", runtime_data.fire_candidate_list)

        # logging neuron activities to the influxdb
        # log_neuron_activity_influx()

        # Forming memories through creation of cell assemblies
        # todo: instead of passing a pain flag simply detect of pain neuron is activated
        neuroplasticity()

        # A deep copy of the FCL to previous FCL
        for _ in runtime_data.fire_candidate_list:
            runtime_data.previous_fcl[_] = set([item for item in runtime_data.fire_candidate_list[_]])

        # print("^^^^^^^^^^ Previous FCL ^^^^^^^^^\n", runtime_data.previous_fcl)

        # Fire all neurons within fire_candidate_list (FCL) or add a delay if FCL is empty
        fire_fcl_contents()

        # Auto-inject/test if applicable
        # todo: move the following functionality to the life.controller to run as a thread
        # Trainer.auto_train()
        # Tester.auto_tester()

        # The following is to have a check point to assess the perf of the in-use genome and make on the fly adj.
        # evolutionary_checkpoint()

        # Monitor cortical activity levels and terminate brain if not meeting expectations
        terminate_on_low_perf()

        # Pain check
        exhibit_pain()

        # Resetting burst_manager detection list
        runtime_data.burst_detection_list = {}

        # # Capture Neuron Membrane Potential Stats
        # capture_mem_potential()

        # Prune all prune candidate synapses
        prune_all_candidates()

        # Burst stats
        burst_stats(burst_start_time)

        # Manage Threads
        # For performance reasons, running this function not on every single burst
        if runtime_data.burst_count % 10 == 0:
            try:
                consciousness_manager()
            except:
                print("consciousness_manager encountered an error!!")

        if not runtime_data.controller_config and runtime_data.burst_publisher:
            controller_handshake()

    print('runtime_data.genome_id = ', runtime_data.genome_id)

    # Initializing the burst_manager engine parameters
    init_burst_engine()

    init_burst_pub()

    # todo: consolidate all the listeners into a class
    # Initialize IPU listener
    if runtime_data.router_address_godot is not None:
        print("runtime_data.router_address_godot=", runtime_data.router_address_godot)
        print("Subscribing Godot incoming port...                                             ++++++++++++++++++++++++")
        godot_listener = Sub(address=runtime_data.router_address_godot)
    if runtime_data.router_address_gazebo is not None:
        print("runtime_data.router_address_gazebo=", runtime_data.router_address_gazebo)
        print("Subscribing Gazebo incoming port...                                            ++++++++++++++++++++++++")
        gazebo_listener = Sub(address=runtime_data.router_address_gazebo)

    else:
        print("Router address is None!")

    # todo: need to figure how to incorporate FCL injection
    # feeder = Feeder()
    # mongo = db_handler.MongoManagement()
    # influxdb = db_handler.InfluxManagement()
    connectome_path = runtime_data.parameters['InitData']['connectome_path']

    if not runtime_data.brain_is_running:
        toggle_brain_status()
        if runtime_data.parameters["Switches"]["capture_brain_activities"]:
            print(settings.Bcolors.HEADER + " *** Warning!!! *** Brain activities are being recorded!!" +
                  settings.Bcolors.ENDC)

    # cortical_list = []
    for cortical_area in runtime_data.cortical_list:
        # cortical_list.append(cortical_area)
        init_fcl(cortical_area)
    # runtime_data.cortical_list = cortical_list

    if runtime_data.parameters["Switches"]["capture_brain_activities"]:
        runtime_data.fcl_history = {}
    # capture_neuron_mp()

    # Live mode condition
    # todo: This segment to be replaced with auto-pilot code
    # print("live mode status: ", runtime_data.parameters["Switches"]["live_mode"], runtime_data.live_mode_status)
    # if runtime_data.parameters["Switches"]["live_mode"] and runtime_data.live_mode_status == 'idle':
    #     runtime_data.live_mode_status = 'learning'
    #     print(settings.Bcolors.RED + "Starting an automated learning process..." + settings.Bcolors.ENDC)
    #     feeder.injection_manager(injection_mode="l1", injection_param="")

    print("\n\nReady to exit burst_manager engine flag:", runtime_data.parameters["Switches"]["ready_to_exit_burst"])

    # This loop runs for the entirety of brain active life
    while not runtime_data.exit_condition:
        burst()


def fcl_feeder(fire_list, fcl_queue):
    # print("Injecting to FCL.../\/\/\/")
    # Update FCL with new input data. FCL is read from the Queue and updated
    flc = fcl_queue.get()
    for item in fire_list:
        flc.append(item)
    fcl_queue.put(flc)

    print("Injected to FCL.../\/\/\/")

    # todo: add the check so if the there is limited IPU activity for multiple consequtive rounds to set a flag

    return


def fire_candidate_locations(fire_cnd_list):
    """Extracts Neuron locations from the fire_candidate_list"""

    # print('***')
    # print(fire_cnd_list)

    neuron_locations = {}
    # Generate a dictionary of cortical areas in the fire_candidate_list
    for item in runtime_data.cortical_list:
        neuron_locations[item] = []

    # Add neuron locations under each cortical area
    for cortical_area in fire_cnd_list:
        for neuron in fire_cnd_list[cortical_area]:
            neuron_locations[cortical_area].append([runtime_data.brain[cortical_area][neuron]["soma_location"][0],
                                                    runtime_data.brain[cortical_area][neuron]["soma_location"][1],
                                                    runtime_data.brain[cortical_area][neuron]["soma_location"][2]])

    return neuron_locations


def load_fcl_in_memory(file_name):
    with open(file_name, 'r') as fcl_file:
        fcl_data = json.load(fcl_file)
    return fcl_data


def latest_fcl_file():
    list_of_files = glob.glob('./fcl_repo/*.json')  # * means all if need specific format then *.csv
    latest_file = max(list_of_files, key=os.path.getctime)
    return latest_file


def toggle_verbose_mode():
    if runtime_data.parameters["Switches"]["verbose"]:
        runtime_data.parameters["Switches"]["verbose"] = False
        print("Verbose mode is Turned OFF!")
    else:
        runtime_data.parameters["Switches"]["verbose"] = True
        print("Verbose mode is Turned On!")


def toggle_brain_status():
    if runtime_data.brain_is_running:
        runtime_data.brain_is_running = False
        print("Brain is not running!")
    else:
        runtime_data.brain_is_running = True
        print("Brain is now running!!!")


def eval(self):
    # Effectiveness check
    if runtime_data.parameters["Switches"]["evaluation_based_termination"]:
        upstream_neuron_count_for_digits = \
            list_upstream_neuron_count_for_digits(digit=self.injector_utf_counter_actual)
        print('## ## ###:', upstream_neuron_count_for_digits)
        if upstream_neuron_count_for_digits[0][1] == 0:
            print(settings.Bcolors.RED +
                  "\n\n\n\n\n\n!!!!! !! !Terminating the brain due to low training capability! !! !!!" +
                  settings.Bcolors.ENDC)
            runtime_data.termination_flag = True
            exit_burst_process()
            self.injector_exit_flag = True
