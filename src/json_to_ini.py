from configparser import ConfigParser

config = ConfigParser()

data = {
  "Timers": {
    "burst_timer": 1,
    "idle_burst_timer": 0.01,
    "auto_train_delay": 3,
    "auto_train_delay2": 50,
    "auto_test_delay": 3,
    "block_size": 10
  },
  "Input": {
    "user_input": "",
    "previous_user_input": "",
    "user_input_param": "",
    "previous_user_input_param": "",
    "opu_char": "X",
    "comprehended_char": []
  },
  "Switches": {
    "verbose": False,
    "vis_show": False,
    "auto_train": False,
    "vis_init_status": False,
    "auto_test_comp_attempt_threshold": 3,
    "ready_to_exit_burst": False,
    "logging_fire": False,
    "folder_backup": False,
    "memory_formation": True,
    "obsolete__plasticity": False,
    "capture_brain_activities": False,
    "visualize_latest_file": False,
    "save_fcl_to_disk": False,
    "save_fcl_to_db": False,
    "save_connectome_to_disk": False,
    "live_mode": True,
    "use_static_genome": True,
    "one_round": False,
    "ipu_vision_dynamic_img_fetch": False,
    "capture_neuron_mp": False,
    "capture_neuron_mp_db": False,
    "evaluation_based_termination": True,
    "use_highest_performing_genome_only": False,
    "influx_stat_logger": False,
    "influx_keep_stats": False,
    "influx_brain_gen_stats": False,
    "global_logger": True,
    "global_timer": True,
    "MNIST_set_option": 2

  },
  "InitData": {
    "read_data_from_memory": True,
    "regenerate_brain": True,
    "connectome_path": "/tmp/feagi/connectome/",
    "rules_path": "./evolutionary/rules.json",
    "static_genome_path": "./feagi/evolutionary/static_genome3.json",
    "fcl_to_visualize": "./fcl_repo/fcl-2018-06-18_14:44:04.243315_A1566B_R.json" ,
    "image_database": "MNIST",
    "activity_history_span": 4,
    "comprehension_span": 1,
    "image_magnification_factor": 200,
    "image_monochromization_threshold": 100,
    "kill_trigger_burst_count": 250,
    "kill_trigger_vision_memory_min": 5,
    "overlap_prevention_constant": 2,
    "max_neighbor_count": 100,
    "influxdb_stat_db": "feagi5",
    "influxdb_evolutionary_db": "feagi_evolutionary"
  },
  "Auto_injector":{
    "epochs": 0,
    "variation_default": 1,
    "exposure_default": 15,
    "utf_default": 3,
    "burst_skip": 15,
    "injector_status": False,
    "injector_burst_skip_counter": 10
  },
  "Auto_tester":{
    "variation_default": 1,
    "exposure_default": 15,
    "utf_default": 3,
    "burst_skip": 15,
    "tester_status": False,
    "tester_burst_skip_counter": 10
  },
  "Logs":{
    "print_mnist_img": True,
    "print_polarized_img": False,
    "print_seen_img": False,
    "print_filtered_img": False,
    "print_activation_counters": True,
    "print_cortical_activity_counters": True,
    "print_mnist_img_info": False,
    "print_plasticity_info": False,
    "print_burst_info": True,
    "print_burst_stats": False,
    "print_brain_gen_activities": True,
    "print_comprehension_queue": True,
    "print_upstream_neuron_stats": True,
    "print_common_neuron_report": True
  },
  "Verbose":{
    "neuron_functions-neuron_update": False,
    "neuron_functions-neuron_fire": False
  },
  "Alerts":{
    "email_fitness_threshold": 1.0
  }
}
    
for key in data:
    config[key] = data[key]
print(config)


with open('./configuration.ini', 'w') as destination:
    config.write(destination)