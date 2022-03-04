#!/bin/bash -efu

TVE_SSH_CONFIG="$HOME/.ssh/tve-dynamic.conf"
SERVER=""

TOKEN="Authorization: PVEAPIToken=$(cat ~/.ssh/tve.tok)"

get_nodes()
{
    curl -s -H "$TOKEN" "https://$SERVER/api2/json/nodes/" | \
        jq -r '.data[].node' 2> /dev/null
}

get_vms()
{
    local node=$1
    curl -s -H "$TOKEN" "https://$SERVER/api2/json/nodes/$node/qemu" \
         | jq -r '.data[] | select((.status == "running") and ((.name|length) < 45))|
                  "\(.vmid):\(.name)"' 2>/dev/null | tr -s '[:blank:]' '_'
}

get_ip()
{
    local node=$1; shift
    local vmid=$1

    curl -s -H "$TOKEN" \
         "https://$SERVER/api2/json/nodes/$node/qemu/$vmid/agent/network-get-interfaces" |
        jq -r '.data.result[] | select(.name == "ens19") | ."ip-addresses"[] |
               select(."ip-address-type" == "ipv4") | [.][0]."ip-address"' 2>/dev/null
}

truncate -s 0 $TVE_SSH_CONFIG
for node in $(get_nodes); do
    (
        get_vms "$node" |
            while IFS=':' read -r vmid vmname; do
                (
                    [ -z "$vmid" -o -z "$vmname" ] && exit
                    vmip=$(get_ip "$node" "$vmid")
                    [ -z "$vmip" ] && exit
                    cat >> $TVE_SSH_CONFIG <<-EOF
Host tve-${vmname// /_}
    HostName $vmip
    User root
    Port 22
    StrictHostKeyChecking no
    IdentityFile ~/.ssh/basealt

EOF
                ) &
            done
    ) &
done

wait
