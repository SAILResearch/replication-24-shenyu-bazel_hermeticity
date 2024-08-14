#!/bin/bash

helpFunction() {
  echo ""
  echo "Usage: $0 -p project_name -t target -c other arguments"
  echo -e "\t-p project name"
  echo -e "\t-s sha of the commit to be built"
  echo -e "\t-t bazel target to be built"
  echo -e "\t-c other arguments"
  exit 1 # Exit script after printing help
}


echo "----------------------------------"

while getopts "p:s:t:c:" opt; do
  case "$opt" in
  p) project_name="$OPTARG" ;;
  s) sha="$OPTARG" ;;
  t) target="$OPTARG" ;;
  c) cmd_args="$OPTARG" ;;
  ?) helpFunction ;; # Print helpFunction in case parameter is non-existent
  esac
done



# Print helpFunction in case parameters are empty
if [ -z "$project_name" ] || [ -z "$target" ]; then
  echo "the value of -p or -t is empty"
  helpFunction
fi

cwd=$(pwd)

cd /repo/"$project_name"/"$project_name" || exit


if [ -z "$sha" ]; then
  main_branch=$(awk -F "/" '{print $NF}' .git/refs/remotes/origin/HEAD)
  git checkout $(git rev-list -n 1 --before="2023-07-31" "$main_branch")

  echo "No sha provided, using HEAD"
else
  echo "Checking out $sha"
  git checkout $sha
fi


if [[ "$project_name" == "brunsli" ]]; then
    git checkout 300af107deecab45bec40c2df90611bb533b606b
fi

if [[ "$project_name" == "cloud-spanner-emulator" ]]; then
    git checkout 748544fd675e177190d45db9633bd015ec7eefef
fi

if [[ "$project_name" == "squzy" ]]; then
    git checkout 0babb18b3ae72179fa4bab237a240e14879fa122
fi

if [[ "$project_name" == "rules_proto" ]]; then
    git checkout 3799dab3ead79435332c90b8770ea31a8af14bbc
fi

#
#if [[ -f BUILD.bazel || -f BUILD ]]; then
#  echo "detected Bazel build files"
#else
#  >&2 echo "no Bazel build files detected"
#  exit 1
#fi
#
#
#bazel clean --expunge
#
#mkdir -p trace
#rm -rf trace/*
#
#echo "----------------------------------"
#echo "starting build"
#
#strace -s 1 -D -xx -o ./trace/trace.log -ttt -ff -y \
#          -e trace=file \
#          bazel build "$target"; bazel shutdown
#
#echo "----------------------------------"
#
#echo "examining build status"
#
#build_log=$(awk "/start running experiment for .*_${project_name}/,0" "${cwd}/experiments.log")
#if echo "$build_log" | grep -q "FAILED: Build did NOT complete successfully"; then
#  echo "Build failed, stop the experiment"
#  exit 1
#fi
#
#
#cd ./trace || exit
#
## remove pipe reads and writes
#sed -i '/\\x70\\x69\\x70\\x65/d' *
#sed -i '/\\x73\\x6f\\x63\\x6b\\x65\\x74/d' *
#
#sed -i '/\+\+\+.*\+\+\+/d' *
#sed -i '/\-\-\-.*\-\-\-/d' *
#sed -i '/.*unfinished.*/d' *
#sed -i '/.*unavailable.*/d' *
#
#
#cat ./* | sort > preprocessed_trace_logs.log
#zip -r "${project_name}_trace_logs.zip" preprocessed_trace_logs.log
#
## remove file reads and writes to /root/.cache/bazel directory for the merged logs
#sed -i '/\\x2f\\x72\\x6f\\x6f\\x74\\x2f\\x2e\\x63\\x61\\x63\\x68\\x65\\x2f\\x62\\x61\\x7a\\x65\\x6c/d' preprocessed_trace_logs.log
#sed -i '/\\x2f\\x68\\x6f\\x6d\\x65\\x2f\\x7a\\x68\\x65\\x6e\\x67\\x73\\x68\\x65\\x6e\\x79\\x75\\x2f\\x2e\\x63\\x61\\x63\\x68\\x65\\x2f\\x62\\x61\\x7a\\x65\\x6c\\x2f/d' preprocessed_trace_logs.log
#cut -d ' ' -f2- preprocessed_trace_logs.log | sort -u -t'=' -k1,1 > merged_trace_logs.log
#sed -i -e 's/^/0.0 /' merged_trace_logs.log
#
#mkdir -p /results/"$project_name"
#mv merged_trace_logs.log /results/"$project_name"/
#mv "${project_name}_trace_logs.zip" /results/"$project_name"/
#
#
#rm -rf trace.log*


