#!/bin/bash

declare -a priorities=("required" "important" "standard")

for priority in "${priorities[@]}"
do
    echo "Priority: $priority"
    pkgs=$(aptitude search "?priority($priority)" -F "%p" --disable-columns)
    while IFS= read -r pkg; do
        printf '%s\n' "$pkg" >> "debian_pkg_priority_$priority.txt"
        apt-cache depends --recurse --no-recommends --no-suggests --no-conflicts --no-breaks --no-replaces --no-enhances "$pkg" | grep "^\w" | sort -u >> "debian_pkg_priority_$priority.txt"
    done <<< "$pkgs"

    sort -u "debian_pkg_priority_$priority.txt" -o "debian_pkg_priority_$priority.txt"
done


for ((i=${#priorities[@]}-1; i>=0; i--))
do
  priority=${priorities[i]}
  for other_priority in "${priorities[@]}"
  do
    if [ "$priority" != "$other_priority" ]
    then
      grep -v -x -f "debian_pkg_priority_$other_priority.txt" "debian_pkg_priority_$priority.txt" > "debian_pkg_priority_$priority.txt.tmp" && mv "debian_pkg_priority_$priority.txt.tmp" "debian_pkg_priority_$priority.txt"
    fi
  done
done