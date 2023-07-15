# chatglm.openvino

This sample shows how to implement a chatglm2-based model with OpenVINO runtime.

**Please notice this repository is only for a functional test, and you can try to quantize the model to further optimize the performance of it**

## How to run it?
1. Install the requirements:

    ```$pip install -r requirements.txt```

2. Export the ONNX model from HuggingFace pipeline:

    ```$mkdir onnx_model```

    ```$python3 export_onnx.py -m {HuggingFace model id} -o ./onnx_model/```

    ***please follow the Licence on HuggingFace and get the approval before downloading llama checkpoints***

3. Run restructured native OpenVINO pipeline:

    ```$python3 generate_ov.py -m  "{HuggingFace model id}" -p "请讲一个有趣的故事" ```