# Replication package for the paper "On Build Hermeticity in Bazel-based Build Systems"


### Abstract


Build hermeticity is critical for achieving reproducible builds by ensuring that the build process is not influenced by changes to the host system. In recent years, new artifact-based build technologies like Bazel, started providing build hermeticity as a core functionality. Yet, no empirical study has evaluated how effectively these new build technologies achieve build hermeticity. This paper studies the build dependencies of 70 Bazel-using open-source projects by analyzing 150 million Linux system calls collected in their build processes. We find that none of the studied projects has a completely hermetic build process, largely due to the non-hermetic build dependencies introduced by the default configuration of key Bazel build rules. Furthermore, as the non-hermetic build dependencies may not be installed by default on new machines and third-party CI environments may update non-hermetic project dependencies at any point in time, developers' builds risk to fail at any point in such environments.




### Authors

Shenyu Zheng

Bram Adams

Ahmed E. Hassan