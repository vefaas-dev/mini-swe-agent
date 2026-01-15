FROM enterprise-public-cn-beijing.cr.volces.com/vefaas-public/all-in-one-sandbox:1.0.0.158

RUN  git clone https://github.com/vefaas-dev/mini-swe-agent.git /home/gem/mini-swe-agent

RUN cp /home/gem/mini-swe-agent/src/minisweagent/config/extra/swebench_vefaas.yaml /home/gem/swebench_vefaas.yaml

RUN cp /home/gem/mini-swe-agent/build/.env /home/gem/.env.example

WORKDIR /home/gem/mini-swe-agent

RUN pip install . -i https://pypi.tuna.tsinghua.edu.cn/simple

RUN chmod -R 777 /home/gem

ENV MSWEA_GLOBAL_CONFIG_DIR=/home/gem/
ENV EVALUATION_DIR=/home/gem/evaluation
ENV HF_ENDPOINT=https://hf-mirror.com

WORKDIR /home/gem