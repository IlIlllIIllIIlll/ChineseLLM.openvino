import os
import sys
import openvino as ov
from transformers import AutoModelForCausalLM
from transformers.generation import GenerationConfig
import torch
from pathlib import Path
import argparse

utils_file_path = Path('.')
sys.path.append(str(utils_file_path))
from utils import flattenize_inputs

ir_model_path = Path('qwen') / Path('ir_model')
if ir_model_path.exists() == False:
    os.mkdir(ir_model_path)
ir_model = ir_model_path / "qwen.xml"

parser = argparse.ArgumentParser(add_help=False)
parser.add_argument('-h',
                    '--help',
                    action='help',
                    help='Show this help message and exit.')
parser.add_argument('-m',
                    '--model_id',
                    default='Qwen/Qwen-7B-Chat',
                    required=False,
                    type=str,
                    help='orignal model path')
parser.add_argument('-cw',
                    '--compress_weight',
                    default=False,
                    required=False,
                    type=bool,
                    help='Weights Compression')
args = parser.parse_args()

model = AutoModelForCausalLM.from_pretrained(args.model_id,
                                             device_map="auto",
                                             trust_remote_code=True).eval()
if args.compress_weight == True:
    print("--- compress weight ---")
    from nncf import compress_weights
    model = compress_weights(model)

# Specify hyperparameters for generation
model.generation_config = GenerationConfig.from_pretrained(
    args.model_id, trust_remote_code=True)
model.config.use_cache = True

outs = model(input_ids=torch.ones((1, 10), dtype=torch.long),
             attention_mask=torch.ones((1, 10), dtype=torch.long))
inputs = ["input_ids"]
outputs = ["logits"]

dynamic_shapes = {"input_ids": {1: "seq_len"}}
for idx in range(len(outs.past_key_values)):
    inputs.extend(
        [f"past_key_values.{idx}.key", f"past_key_values.{idx}.value"])
    dynamic_shapes[inputs[-1]] = {1: "past_sequence + 1"}
    dynamic_shapes[inputs[-2]] = {1: "past_sequence + 1"}
    outputs.extend([f"present.{idx}.key", f"present.{idx}.value"])

dummy_inputs = {
    "input_ids": torch.ones((1, 1), dtype=torch.long),
    "past_key_values": outs.past_key_values
}

model.config.torchscript = True
ov_model = ov.convert_model(model, example_input=dummy_inputs)
for inp_name, m_input, input_data in zip(
        inputs, ov_model.inputs, flattenize_inputs(dummy_inputs.values())):
    input_node = m_input.get_node()
    if input_node.element_type == ov.Type.dynamic:
        m_input.get_node().set_element_type(ov.Type.f32)
    shape = list(input_data.shape)
    if inp_name in dynamic_shapes:
        for k in dynamic_shapes[inp_name]:
            shape[k] = -1
    input_node.set_partial_shape(ov.PartialShape(shape))
    m_input.get_tensor().set_names({inp_name})

for out, out_name in zip(ov_model.outputs, outputs):
    out.get_tensor().set_names({out_name})

ov_model.validate_nodes_and_infer_types()
ov.save_model(ov_model, ir_model)