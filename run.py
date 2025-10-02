# Copyright 2025 Chair of EDA, Technical University of Munich
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

import argparse
import textwrap
import pathlib
import os
import subprocess
import csv

def get_results_csv_path():
    mlonmcu_home = os.environ.get("MLONMCU_HOME")
    if not mlonmcu_home:
        raise EnvironmentError("MLONMCU_HOME environment variable is not set.")
    return os.path.join(mlonmcu_home, "temp", "sessions", "latest", "report.csv")

def parse_simulation_results(rows):
    row = rows[-1]  # Last row
    run_cycles = int(row["Run Cycles"])
    run_instructions = int(row["Run Instructions"])
    run_cpi = float(row["Run CPI"])
    return run_cycles, run_instructions, run_cpi

def parse_results_csv(mode):
    results_path = get_results_csv_path()
    with open(results_path, newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        rows = list(reader)

    if not rows:
        raise ValueError("No data found in results.csv")

    if mode == "simulate":
        print("Results from Simulation")
        return parse_simulation_results(rows)
    elif mode == "deploy":
        return None
    else:
        raise ValueError(f"Unsupported mode: {mode}")


def main():
    
    ## PARSE ARGUMENTS ##
    
    parser = argparse.ArgumentParser(description="Run simulation or deployment.")
    parser.add_argument("kws_model", choices=["kws_1"], help="KWS model to apply")
    parser.add_argument("-a", "--autotune", choices=["default"], default="default", help="Autotuning configuration to use (default: default)")
    parser.add_argument("-p", "--print", action="store_true", help="Increase output verbosity")
    parser.add_argument("-o", "--optimization", choices=["0", "2", "s"], default="s", help="Compiler optimization level: 0, 2, or s (default: s)")
    subparsers = parser.add_subparsers(dest="mode", required=True, help="Mode to run: simulate or deploy")

    # Simulate subcommand
    simulate_parser = subparsers.add_parser("simulate", help="Run simulation")
    simulate_parser.add_argument("-c", "--core_model", default="esp32c3", help="Core model to simulate (default: esp32c3)")

    # Deploy subcommand
    deploy_parser = subparsers.add_parser("deploy", help="Run deployment")
    deploy_parser.add_argument("-w", "--wait", action="store_true", help="Wait for user input befor flashing the device")
    deploy_parser.add_argument("-f", "--flash_only", action="store_true", help="Only flash the device without connecting to serial monitor")

    args = parser.parse_args()

    extra_args = ""
    if args.print:
        extra_args = "-v"

    
    ## PATHS AND ENVIRONMENT VARIABLES ##

    ENV_HOME = pathlib.Path(__file__).parent.resolve()
    MLONMCU = ENV_HOME / "mlonmcu"
    MLONMCU_HOME = MLONMCU / "workspace_kws"
    os.environ["MLONMCU_HOME"] = str(MLONMCU_HOME) # Need this as environment variable

    TARGET_SW = ENV_HOME / "target_sw"
    PLATFORM_TEMPLATE = TARGET_SW / "app/micro_kws_esp32devboard_perf"
    if args.kws_model == "kws_1":
        KWS_DIR = TARGET_SW / "kws/kws_1"
        KWS_MODEL = KWS_DIR / "micro_kws_student_quantized.tflite"
        if args.autotune == "default":
            AUTOTUNED_RESULTS = KWS_DIR / "autotune/micro_kws_student_tuning_log_nchw_best.txt"
        else:
            raise ValueError(f"Unknown autotune configuration: {args.autotune}")
    else:
        raise ValueError(f"Unknown kws model: {args.kws_model}")

    ESP32C3_GCC_INSTALL = MLONMCU_HOME / "deps/install/espidf/tools/riscv32-esp-elf/esp-14.2.0_20241119/riscv32-esp-elf" 

    ## RUN ENVRIONMENT ##
    
    if args.mode == "simulate":
        print("Simulate mode selected.")
        cmd = textwrap.dedent(
            f"""\
            source {str(MLONMCU)}/venv/bin/activate
            python3 -m mlonmcu.cli.main flow run {str(KWS_MODEL)} \
            --target etiss_perf -c run.export_optional=1 \
            -c etiss_perf.print_outputs={int(args.print)} \
            --backend tvmaotplus -c tvmaotplus.desired_layout=NCHW -c tvmaot.desired_layout=NCHW \
            -f autotuned -c autotuned.results_file={str(AUTOTUNED_RESULTS)} \
            -c riscv_gcc_rv32.install_dir={ESP32C3_GCC_INSTALL} -c riscv_gcc_rv32.name=riscv32-esp-elf \
            -c etiss_perf.fpu=none -c etiss_perf.atomic=0 -c etiss_perf.compressed=0 \
            -f perf_sim -c mlif.optimize={args.optimization} -c perf_sim.core={args.core_model} -c etiss_perf.flash_start=0x42000000 -c etiss_perf.flash_size=0x800000 {extra_args}
            """
        )

    elif args.mode == "deploy":
        print("Deploy mode selected.")
        cmd = textwrap.dedent(
            f"""\
            source {str(MLONMCU)}/venv/bin/activate
            python3 -m mlonmcu.cli.main flow run {str(KWS_MODEL)} \
            --target esp32c3 --platform espidf \
            -c espidf.print_outputs={int(args.print)} -c esp32c3.print_outputs={int(args.print)} -c run.export_optional=1 \
            --backend tvmaotplus -c tvmaotplus.desired_layout=NCHW -c tvmaot.desired_layout=NCHW \
            -f autotuned -c autotuned.results_file={str(AUTOTUNED_RESULTS)} \
            -c espidf.project_template={str(PLATFORM_TEMPLATE)} -c espidf.wait_for_user={int(args.wait)} \
            -c espidf.append_sdkconfig_defaults=1 -c espidf.flash_only={int(args.flash_only)}\
            -c riscv_gcc_rv32.install_dir={ESP32C3_GCC_INSTALL} -c riscv_gcc_rv32.name=riscv32-esp-elf \
            -c espidf.optimize={args.optimization} -c espidf.extra_cmake_defs="{{'CONFIG_ENABLE_WIFI': 1}}" {extra_args}
            """
        )

    #elif args.mode == "deploy":
    #    print("Deploy mode selected.")
    #    cmd = textwrap.dedent(
    #        f"""\
    #        source {str(MLONMCU)}/venv/bin/activate
    #        python3 -m mlonmcu.cli.main flow run {str(KWS_MODEL)} \
    #        --target esp32c3 --platform espidf \
    #        -c espidf.print_outputs={int(args.print)} -c esp32c3.print_outputs={int(args.print)} -c run.export_optional=1 \
    #        --backend tvmaotplus -c tvmaotplus.desired_layout=NCHW -c tvmaot.desired_layout=NCHW \
    #        -f autotuned -c autotuned.results_file={str(AUTOTUNED_RESULTS)} \
    #        -c espidf.project_template=micro_kws_esp32devboard_perf -c espidf.wait_for_user={args.wait} -c espidf.flash_only={int(args.flash_only)}\
    #        -c riscv_gcc_rv32.install_dir={ESP32C3_GCC_INSTALL} -c riscv_gcc_rv32.name=riscv32-esp-elf \
    #        -c espidf.optimize={args.optimization} -c espidf.extra_cmake_defs="{{'CONFIG_ENABLE_WIFI': 1}}" {extra_args}
    #        """
    #    )

    # Call mlonmcu command
    result = subprocess.run(cmd, shell=True)
    if result.returncode == 0:
        print("\nCommand executed successfully.\n")
        result = parse_results_csv(args.mode)
        if result:
            run_cycles, run_instructions, run_cpi = result
            print(f"Compiler Optimization: {args.optimization}")
            print(f"Model Run Cycles: {run_cycles}")
            print(f"Model Run Instructions: {run_instructions}")
            print(f"Model Run CPI: {run_cpi:.6f}")
    else:
        print(f"\nCommand failed with return code: {result.returncode}")
        print("Error Output:\n", result.stderr)


if __name__ == "__main__":
    main()


