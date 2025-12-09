#client_runner.py
# this file is to start fl process for that client which is unprofessional to do directly in flask file.

# client_runner.py
import logging
from examples.minimal.minimal_MLEngine import (
    init_models,
    training,
    compute_performance,
    judge_termination,
    prep_test_data
)
from fl_main.agent.client import Client

logging.basicConfig(level=logging.INFO)

def main(agent_name):
    logging.info(f"--- Starting FL Client for {agent_name} ---")

    # Create FL client
    fl_client = Client()
    fl_client.agent_name = agent_name

    # Init models (structure only)
    initial_models = training(dict(), init_flag=True)

    # Send initial model structure
    fl_client.send_initial_model(initial_models)

    # Start core FL communication (threads start)
    fl_client.start_fl_client()

    training_count = 0
    gm_arrival_count = 0

    # Actual FL training loop
    while judge_termination(training_count, gm_arrival_count):

        # Wait for global model
        global_models = fl_client.wait_for_global_model()
        gm_arrival_count += 1
        print("Received Global Models:", global_models)

        # Evaluate global models (optional)
        perf_global = compute_performance(global_models, prep_test_data())

        # Local training
        new_models = training(global_models)
        training_count += 1
        print("Local Trained Models:", new_models)

        # Evaluate local models
        local_perf = compute_performance(new_models, prep_test_data())

        # Send model update
        #fl_client.send_trained_model(new_models, model_id=1, performance=local_perf)
        fl_client.send_trained_model(new_models, 1, local_perf)

    logging.info("--- FL client terminated ---")

if __name__ == "__main__":
    import sys
    agent_name = sys.argv[1] if len(sys.argv) > 1 else "default_agent"
    main(agent_name)
