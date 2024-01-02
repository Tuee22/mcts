ARG BASE_IMAGE
FROM ${BASE_IMAGE}
ARG REQUIREMENTS
ARG DEBIAN_FRONTEND=noninteractive
RUN apt update && apt install -y software-properties-common
RUN add-apt-repository -y ppa:ubuntu-toolchain-r/test
RUN apt update && apt install -y gcc-13 g++-13 libboost-all-dev git curl wget valgrind cppcheck
RUN apt install -y python3 python3-dev python3-pip
#RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
RUN update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-13 1 --slave /usr/bin/g++ g++ /usr/bin/g++-13

# update package managers 
RUN python3 -m pip install --upgrade pip setuptools wheel 

# install python packages
WORKDIR /home
#RUN python3 -m pip install dask[complete] numba scipy scons cupy-cuda12x jupyterlab==3.6.6 plotly ipywidgets jupyter-dash torch pytorch-lightning tables pyarrow s3fs mypy pandas-stubs torchvision
COPY ${REQUIREMENTS} /home
RUN python3 -m pip install -r requirements.txt

# set up python libs
ENV PYTHONPATH "${PYTHONPATH}:/home/python/"
COPY ./python /home/python/

# build c++ code 
COPY ./src /home/src/
WORKDIR /home/src
RUN scons
RUN cp _corridors_mcts.so /home/python/corridors/
WORKDIR /home
RUN rm -rf src/

EXPOSE 8888 8786 8787
CMD jupyter lab --ip=0.0.0.0 --port=8888 --LabApp.token="" --notebook-dir='/home' --no-browser --allow-root