# Replication package for the paper "On Build Hermeticity in Bazel-based Build Systems"


### Abstract


BA hermetic build system manages its own build dependencies, isolated from the host file system, thereby securing the build process. Although, in recent years, new artifact-based build technologies like Bazel offer build hermeticity as a core functionality, no empirical study has evaluated how effectively these new build technologies achieve build hermeticity. This paper studies 2,439 non-hermetic build dependency packages of 70 Bazel-using open-source projects by analyzing 150 million Linux system file calls collected in their build processes. We found that none of the studied projects has a completely hermetic build process, largely due to the use of non-hermetic top-level toolchains. 71.9\% of these are Linux utility toolchains that in principle could be managed by Bazel, while 38.1\% are programming language-related toolchains introduced by the default configuration of key Bazel build rules. Furthermore, we evaluate the risks of non-hermetic build dependencies when building projects on new machines or within CI.


### Project Structure
This replication package contains the following files:


- `cirunner/`: The scripts used to analyze version changes of installed packages on GitHub Actions and CircleCI runners
- `data/`: The raw data of our study
  - For the full dataset, please refer to the [Zenodo repository](https://zenodo.org/records/13324237)
- `data_process/`: The scripts used to process the raw data
- `experiments/`: The scripts used to run the experiments
- `externalmanaged/`: The scripts used to identify the non-hermetic dependencies that are externally managed 
- `priority`: The scripts used to query the priority of Debian packages
- `strace_parser`: The scripts used to parse the strace logs
- `visualization/`: The scripts used to visualize the results

### Start Experiment

#### Setup

**Install the required packages**
```bash
apt-get update && \
apt-get -y install \
        make curl apt-utils \
        python \
        python3 \
        python-pkg-resources \
        python3-pkg-resources \
        software-properties-common \
        unzip \
        git \
        build-essential \
        nodejs npm \
        openjdk-17-jdk


wget https://go.dev/dl/go1.19.7.linux-amd64.tar.gz -o go1.19.7.linux-amd64.tar.gz
tar -C /usr/local -xzf go1.19.7.linux-amd64.tar.gz
export PATH="/usr/local/go/bin:${PATH}"

curl https://sh.rustup.rs -sSf | bash -s -- -y
echo 'source $HOME/.cargo/env' >> $HOME/.bashrc
export PATH="/root/.cargo/bin:${PATH}"

wget https://github.com/bazelbuild/bazelisk/releases/download/v1.16.0/bazelisk-linux-amd64 -o /usr/local/bin/bazel
chmod +x /usr/local/bin/bazel


```

**Install the required Python packages**
```bash
cd experiments/

pip install -r requirements.txt

```

#### Start the experiment
```bash
cd experiments/
bash start_experiments.sh

# the results are stored on ./results/directory
```

### Authors

Shenyu Zheng

Bram Adams

Ahmed E. Hassan