# GenerIoT_KWS_workspace
Workspace to simulate and deploy a key-word-spotting (KWS) application to the ESP32C3.

## Setup

### Clone repository

Clone this repository and navigate to its top folder. (The given example uses an SSH-based link; adapt if necessary)

    $ git clone git@github.com:tum-ei-eda/GenerIoT_KWS_workspace.git <YOUR_WORKSPACE_NAME>
    $ cd <YOUR_WORKSPACE_NAME>

Initialize the required submodules

    $ git submodule update --init --recursive

### Setup MLonMCU

Create a virtual environment for MLonMCU

    $ cd mlonmcu
    $ python3 -m venv venv
    $ source venv/bin/activate
    $ pip install -e .

Run the following sequence to setup MLonMCU (make sure you are inside the `mlonmcu` directory and the virtual environment is activated). This step will install required dependencies (e.g. ESP-IDF, ETISS simulator) and can require some time to finish.

    $ python3 -m mlonmcu.cli.main init -t kws workspace_kws --clone-models --non-interactive --allow-exists
    $ export MLONMCU_HOME=$(pwd)/workspace_kws
    $ python3 -m mlonmcu.cli.main setup -g
    <It might be necessary to upgrade pip here by calling: python3 -m pip install --upgrade pip setuptools wheel>
    $ python3 -m pip install -r $MLONMCU_HOME/requirements_addition.txt
    $ python3 -m mlonmcu.cli.main setup -v --progress

## Usage

The workspace supports mainly two modes: `simulate` and `deploy`

### Simulation

To run a simulation of the KWS-model's (kws_1) performance on the ESP32C3 core, run:

    $ python3 run.py kws_1 [--print] simulate --core_model="esp32c3"

### Deploy

To deploy the KWS-model (kws_1) and the supporting WiFi-application to an ESP32C3 device and run the application in connected mode, call:

    $ python3 run.py kws_1 [--print] deploy --wait