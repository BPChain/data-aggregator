FROM ethereum/client-go:latest

RUN apk add --update linux-headers git bash
RUN apk add --update python3 musl-dev gcc python3-dev py3-netifaces py3-psutil nodejs nodejs-npm
RUN npm install -g truffle
RUN pip3 install --upgrade pip
RUN pip3 install --upgrade pip setuptools
RUN pip3 install git+https://github.com/BPChain/scenario-orchestration-service.git#
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY .ethash root/.ethash
COPY files root/files
RUN cd /root/files && npm install
RUN chmod +x /root/files/start_eth_node.sh
RUN chmod +x /root/files/start_bootstrap.sh
RUN chmod +x /root/files/start_eth_contract_deployer.sh
