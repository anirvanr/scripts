#!/bin/bash

# shell script to create a simple mongodb replica set (tested on CentOS Linux release 7.6.1810,db version v4.0.6)

function finish {
    pids=(`cat ~/mongosvr/rs-*.pid`)
    for pid in "${pids[@]}"
    do
        kill $pid
        wait $pid
    done
}
trap finish EXIT


mkdir -p ~/mongosvr/rs-0
mkdir -p ~/mongosvr/rs-1
mkdir -p ~/mongosvr/rs-2

mongod --dbpath ~/mongosvr/rs-0 --replSet set --port 27091 \
    --pidfilepath ~/mongosvr/rs-0.pid --smallfiles --oplogSize 128 2>&1 &

mongod --dbpath ~/mongosvr/rs-1 --replSet set --port 27092 \
    --pidfilepath ~/mongosvr/rs-1.pid --smallfiles --oplogSize 128 2>&1 &

mongod --dbpath ~/mongosvr/rs-2 --replSet set --port 27093 \
    --pidfilepath ~/mongosvr/rs-2.pid --smallfiles --oplogSize 128 2>&1 &

# wait a bit for the first server to come up
sleep 5

# call rs.initiate({...})
cfg="{
    _id: 'set',
    members: [
        {_id: 1, host: 'localhost:27091'},
        {_id: 2, host: 'localhost:27092'},
        {_id: 3, host: 'localhost:27093'}
    ]
}"
mongo localhost:27091 --eval "JSON.stringify(db.adminCommand({'replSetInitiate' : $cfg}))"

# sleep forever
cat
