from enterprise-public-cn-beijing.cr.volces.com/vefaas-public/all-in-one-sandbox:1.0.0.158

COPY mini-swe-agent-vefaas /home/gem/mini-swe-agent

COPY mini-swe-agent-vefaas/src/minisweagent/config/extra/swebench_vefaas.yaml /home/gem/swebench_vefaas.yaml

WORKDIR /home/gem/mini-swe-agent

RUN pip install . -i https://pypi.tuna.tsinghua.edu.cn/simple

RUN chmod -R 777 /home/gem

ENV MSWEA_GLOBAL_CONFIG_DIR /home/gem/
ENV EVALUATION_DIR /home/gem/evaluation

WORKDIR /home/gem