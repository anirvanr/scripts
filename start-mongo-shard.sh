#!/usr/bin/env bash
set -e

# This script will start three shards, a config server and a mongos, all on the current machine.
# This script is only for testing purposes.  In production, you would run each of these servers on a different machine.
# It was written for Mongo v4.0.6

# clean everything up
echo "killing mongod and mongos"
pkill -u $UID mongod || true
pkill -u $UID mongos || true
echo "removing data files"
rm -rf data/config-*
rm -rf data/shard*

sleep 1

# start a replica set and tell it that it will be shard0
rm s0-r0.log s0-r1.log s0-r2.log || true
mkdir -p data/shard0/rs0 data/shard0/rs1 data/shard0/rs2
mongod --replSet s0 --logpath "s0-r0.log" --dbpath data/shard0/rs0 --port 37017 --fork --shardsvr --smallfiles
mongod --replSet s0 --logpath "s0-r1.log" --dbpath data/shard0/rs1 --port 37018 --fork --shardsvr --smallfiles
mongod --replSet s0 --logpath "s0-r2.log" --dbpath data/shard0/rs2 --port 37019 --fork --shardsvr --smallfiles

sleep 5

# connect to one server and initiate the set
mongo --port 37017 << 'EOF'
config = { _id: "s0", members:[
          { _id : 0, host : "localhost:37017" },
          { _id : 1, host : "localhost:37018" },
          { _id : 2, host : "localhost:37019" }]};
rs.initiate(config)
EOF

# start a replicate set and tell it that it will be a shard1
rm s1-r0.log s1-r1.log s1-r2.log || true
mkdir -p data/shard1/rs0 data/shard1/rs1 data/shard1/rs2
mongod --replSet s1 --logpath "s1-r0.log" --dbpath data/shard1/rs0 --port 47017 --fork --shardsvr --smallfiles
mongod --replSet s1 --logpath "s1-r1.log" --dbpath data/shard1/rs1 --port 47018 --fork --shardsvr --smallfiles
mongod --replSet s1 --logpath "s1-r2.log" --dbpath data/shard1/rs2 --port 47019 --fork --shardsvr --smallfiles

sleep 5

mongo --port 47017 << 'EOF'
config = { _id: "s1", members:[
          { _id : 0, host : "localhost:47017" },
          { _id : 1, host : "localhost:47018" },
          { _id : 2, host : "localhost:47019" }]};
rs.initiate(config)
EOF

# start a replicate set and tell it that it will be a shard2
rm s2-r0.log s2-r1.log s2-r2.log || true
mkdir -p data/shard2/rs0 data/shard2/rs1 data/shard2/rs2
mongod --replSet s2 --logpath "s2-r0.log" --dbpath data/shard2/rs0 --port 57017 --fork --shardsvr --smallfiles
mongod --replSet s2 --logpath "s2-r1.log" --dbpath data/shard2/rs1 --port 57018 --fork --shardsvr --smallfiles
mongod --replSet s2 --logpath "s2-r2.log" --dbpath data/shard2/rs2 --port 57019 --fork --shardsvr --smallfiles

sleep 5

mongo --port 57017 << 'EOF'
config = { _id: "s2", members:[
          { _id : 0, host : "localhost:57017" },
          { _id : 1, host : "localhost:57018" },
          { _id : 2, host : "localhost:57019" }]};
rs.initiate(config)
EOF

# now start 3 config servers
rm cfg-a.log cfg-b.log cfg-c.log || true
mkdir -p data/config/config-a data/config/config-b data/config/config-c
mongod --replSet cs --logpath "cfg-a.log" --dbpath data/config/config-a --port 57040 --fork --configsvr --smallfiles
mongod --replSet cs --logpath "cfg-b.log" --dbpath data/config/config-b --port 57041 --fork --configsvr --smallfiles
mongod --replSet cs --logpath "cfg-c.log" --dbpath data/config/config-c --port 57042 --fork --configsvr --smallfiles

sleep 5

mongo --port 57040 << 'EOF'
config = { _id: "cs", configsvr: true, members:[
          { _id : 0, host : "localhost:57040" },
          { _id : 1, host : "localhost:57041" },
          { _id : 2, host : "localhost:57042" }]};
rs.initiate(config)
EOF

# now start the mongos on port 27018
rm mongos-1.log || true
sleep 5
mongos --port 27018 --logpath "mongos-1.log" --configdb cs/localhost:57040,localhost:57041,localhost:57042 --fork
echo "Waiting 60 seconds for the replica sets to fully come online"
sleep 60
echo "Connnecting to mongos and enabling sharding"

# add shards and enable sharding on the test db
mongo --port 27018 << 'EOF'
db.adminCommand( { addshard : "s0/"+"localhost:37017" } );
db.adminCommand( { addshard : "s1/"+"localhost:47017" } );
db.adminCommand( { addshard : "s2/"+"localhost:57017" } );
db.adminCommand({enableSharding: "test"});
EOF

sleep 5

echo "Done setting up sharded environment on localhost"
echo "================================================"
ps aux | grep " mongo[ds] "
