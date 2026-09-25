from pathlib import Path
import yaml
from .headway import FixedBlock, MovingBlock

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config"


def load_signalling(path=CONFIG / "corridor.yaml"):
    raw = yaml.safe_load(Path(path).read_text())["signalling"]
    fb, mb = raw["fixed_block"], raw["moving_block"]
    return (FixedBlock(fb["block_length_m"], fb["overlap_m"], fb["route_setting_and_sighting_s"]),
            MovingBlock(mb["safety_margin_m"], mb["accuracy_abs_m"], mb["accuracy_rel"],
                        mb["transponder_spacing_m"], mb["report_interval_s"],
                        mb["comm_latency_s"], mb["system_processing_s"]))
