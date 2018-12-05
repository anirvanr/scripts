#!/bin/bash

##---------- Purpose : To quickly check and report health status in a linux system.----------##
##---------- Tested on : RHEL7/6/5/, SLES12/11, Ubuntu14, Mint16, Boss6(Debian) variants.----##
##---------- Updated version : v1.0 (Updated on 5th-Dec-2018) -----------------------------##
##-----NOTE: This script requires root privileges, otherwise you could run the script -------##
##---- as a sudo user who got root privileges. ----------------------------------------------##
##----------- "sudo /bin/bash <ScriptName>" -------------------------------------------------##

S="************************************"
D="-------------------------------------"

MOUNT=$(mount|egrep -iw "ext4|ext3|xfs|gfs|gfs2|btrfs"|sort -u -t' ' -k1,2)
FS_USAGE=$(df -PTh|egrep -iw "ext4|ext3|xfs|gfs|gfs2|btrfs"|sort -k6n|awk '!seen[$1]++')
IUSAGE=$(df -PThi|egrep -iw "ext4|ext3|xfs|gfs|gfs2|btrfs"|sort -k6n|awk '!seen[$1]++')

#--------Checking the availability of sysstat package..........#
if [ ! -x /usr/bin/mpstat ]
then
    printf "\nError : Either \"mpstat\" command not available OR \"sysstat\" package is not properly installed. Please make sure this package is installed and working properly!, then run this script.\n\n"
    exit 1
fi

printf '\n\e[1;34m%-6s\e[m\n' "Operating System Details"
printf '\e[1;34m%-6s\e[m\n' "$D"
printf "Hostname :" $(hostname -f > /dev/null 2>&1) && printf " $(hostname -f)" || printf " $(hostname -s)"

[ -x /usr/bin/lsb_release ] &&  echo -e "\nOperating System :" $(lsb_release -d|awk -F: '{print $2}'|sed -e 's/^[ \t]*//')  || echo -e "\nOperating System :" $(cat /etc/system-release)
echo -e "Kernel Version :" $(uname -r)
printf "OS Architecture :" $(arch | grep x86_64 2>&1 > /dev/null) && printf " 64 Bit OS\n"  || printf " 32 Bit OS\n"

#--------Print system uptime-------#
UPTIME=$(uptime)
echo $UPTIME|grep day 2>&1 > /dev/null
if [ $? != 0 ]
then
  echo $UPTIME|grep -w min 2>&1 > /dev/null && echo -e "System Uptime : "$(echo $UPTIME|awk '{print $2" by "$3}'|sed -e 's/,.*//g')" minutes"  || echo -e "System Uptime : "$(echo $UPTIME|awk '{print $2" by "$3" "$4}'|sed -e 's/,.*//g')" hours"
else
  echo -e "System Uptime :" $(echo $UPTIME|awk '{print $2" by "$3" "$4" "$5" hours"}'|sed -e 's/,//g')
fi
echo -e "Current System Date & Time : "$(date +%c)


#--------Check for any read-only file systems--------#
printf '\n\e[1;34m%-6s\e[m\n' "Checking For Read-only File System[s]"
printf '\e[1;34m%-6s\e[m\n' "$D$D"
echo "$MOUNT"|grep -w \(ro\) && echo -e "\n.....Read Only file system[s] found"|| echo -e ".....No read-only file system[s] found. "


#--------Check for currently mounted file systems--------#
printf '\n\e[1;34m%-6s\e[m\n' "Checking For Currently Mounted File System[s]"
printf '\e[1;34m%-6s\e[m\n' "$D$D"
echo "$MOUNT"|column -t

#--------Check disk usage on all mounted file systems--------#
printf '\n\e[1;34m%-6s\e[m\n' "Checking For Disk Usage On Mounted File System[s]"
echo -e "( 0-90% = OK/HEALTHY, 90-95% = WARNING, 95-100% = CRITICAL )"
printf '\e[1;34m%-6s\e[m\n' "$D$D"
echo -e "Mounted File System[s] Utilization (Percentage Used):\n"

echo "$FS_USAGE"|awk '{print $1 " "$7}' > /tmp/s1.out
echo "$FS_USAGE"|awk '{print $6}'|sed -e 's/%//g' > /tmp/s2.out
> /tmp/s3.out

for i in $(cat /tmp/s2.out);
do
{
  if [ $i -ge 95 ];
   then
     echo -e $i"% ------------------Critical" >> /tmp/s3.out;
   elif [[ $i -ge 90 && $i -lt 95 ]];
   then
     echo -e $i"% ------------------Warning" >> /tmp/s3.out;
   else
     echo -e $i"% ------------------Good/Healthy" >> /tmp/s3.out;
  fi
}
done
paste -d"\t" /tmp/s1.out /tmp/s3.out|column -t

#--------Check for any zombie processes--------#
printf '\n\e[1;34m%-6s\e[m\n' "Checking For Zombie Processe"
printf '\e[1;34m%-6s\e[m\n' "$D"
ps -eo stat|grep -w Z 1>&2 > /dev/null
if [ $? == 0 ]
then
  echo -e "Number of zombie process on the system are :" $(ps -eo stat|grep -w Z|wc -l)
  echo -e "\n  Details of each zombie processes found    "
  echo -e "  $D"
  ZPROC=$(ps -eo stat,pid|grep -w Z|awk '{print $2}')
  for i in $(echo "$ZPROC")
  do
      ps -o pid,ppid,user,stat,args -p $i
  done
else
 echo -e "No zombie processes found on the system."
fi

#--------Check Inode usage--------#
printf '\n\e[1;34m%-6s\e[m\n' "Checking For INode Usage"
echo -e "( 0-90% = OK/HEALTHY, 90-95% = WARNING, 95-100% = CRITICAL )"
printf '\e[1;34m%-6s\e[m\n' "$D$D"
echo -e "INode Utilization (Percentage Used):\n"

echo "$IUSAGE"|awk '{print $1" "$7}' > /tmp/s1.out
echo "$IUSAGE"|awk '{print $6}'|sed -e 's/%//g' > /tmp/s2.out
> /tmp/s3.out

for i in $(cat /tmp/s2.out);
do
  if [[ $i = *[[:digit:]]* ]];
  then
  {
  if [ $i -ge 95 ];
  then
    echo -e $i"% ------------------Critical" >> /tmp/s3.out;
  elif [[ $i -ge 90 && $i -lt 95 ]];
  then
    echo -e $i"% ------------------Warning" >> /tmp/s3.out;
  else
    echo -e $i"% ------------------Good/Healthy" >> /tmp/s3.out;
  fi
  }
  else
    echo -e $i"% (Inode Percentage details not available)" >> /tmp/s3.out
  fi
done
paste -d"\t" /tmp/s1.out /tmp/s3.out|column -t

#--------Check for RAM Utilization--------#
printf '\n\e[1;34m%-6s\e[m\n' "Checking Memory Usage Details"
echo -e "( 0-95% = OK/HEALTHY, 95-98% = WARNING, 98-100% = CRITICAL )"
printf '\e[1;34m%-6s\e[m\n' "$D$D"

#Set default values
optMW=95
optMC=98
optSW=95
optSC=98

array=( $(cat /proc/meminfo | egrep 'MemTotal|MemFree|Buffers|Cached|SwapTotal|SwapFree' |awk '{print $1 " " $2}' |tr '\n' ' ' |tr -d ':' |awk '{ printf("%i %i %i %i %i %i %i", $2, $4, $6, $8, $10, $12, $14) }') )

memTotal_k=${array[0]}
memTotal_b=$(($memTotal_k*1024))
memFree_k=${array[1]}
memFree_b=$(($memFree_k*1024))
memBuffer_k=${array[2]}
memBuffer_b=$(($memBuffer_k*1024))
memCache_k=${array[3]}
memCache_b=$(($memCache_k*1024))
memTotal_m=$(($memTotal_k/1024))
memFree_m=$(($memFree_k/1024))
memBuffer_m=$(($memBuffer_k/1024))
memCache_m=$(($memCache_k/1024))
memUsed_b=$(($memTotal_b-$memFree_b-$memBuffer_b-$memCache_b))
memUsed_m=$(($memTotal_m-$memFree_m-$memBuffer_m-$memCache_m))
memUsedPrc=$((($memUsed_b*100)/$memTotal_b))
swapTotal_k=${array[5]}
swapTotal_b=$(($swapTotal_k*1024))
swapFree_k=${array[6]}
swapFree_b=$(($swapFree_k*1024))
swapUsed_k=$(($swapTotal_k-$swapFree_k))
swapUsed_b=$(($swapUsed_k*1024))
swapTotal_m=$(($swapTotal_k/1024))
swapFree_m=$(($swapFree_k/1024))
swapUsed_m=$(($swapTotal_m-$swapFree_m))

if [ $swapTotal_k -eq 0 ]; then
    swapUsedPrc=0
else
    swapUsedPrc=$((($swapUsed_k*100)/$swapTotal_k))
fi

mem="[MEMORY] Total: $memTotal_m MB - Used: $memUsed_m MB - $memUsedPrc%"
swap="[SWAP] Total: $swapTotal_m MB - Used: $swapUsed_m MB - $swapUsedPrc%"

if [ $memUsedPrc -ge $optMC ] || [ $swapUsedPrc -ge $optSC ]; then
  echo -e "$mem    $swap ------------------Critical"
elif [ $memUsedPrc -ge $optMW ] || [ $swapUsedPrc -ge $optSW ]; then
    echo -e "$mem    $swap ------------------Warning"
else
  echo -e "$mem    $swap ------------------Good/Healthy"
fi

#--------Check for Processor Utilization (current data)--------#
printf '\n\e[1;34m%-6s\e[m\n' "Checking For Processor Utilization"
printf '\e[1;34m%-6s\e[m\n' "$D$D"
echo -e "Manufacturer: "$(dmidecode -s processor-manufacturer|uniq)
echo -e "Processor Model: "$(dmidecode -s processor-version|uniq)
if [ -e /usr/bin/lscpu ]
then
{
    echo -e "No. Of Processor(s) :" $(lscpu|grep -w "Socket(s):"|awk -F: '{print $2}')
    echo -e "No. of Core(s) per processor :" $(lscpu|grep -w "Core(s) per socket:"|awk -F: '{print $2}')
}
else
{
    echo -e "No. Of Processor(s) Found :" $(grep -c processor /proc/cpuinfo)
    echo -e "No. of Core(s) per processor :" $(grep "cpu cores" /proc/cpuinfo|uniq|wc -l)
}
fi
echo -e "\nCurrent Processor Utilization Summary :\n"
mpstat|tail -2

#--------Check for load average (current data)--------#
printf '\n\e[1;34m%-6s\e[m\n' "Checking For Load Average"
printf '\e[1;34m%-6s\e[m\n' "$D$D"
echo -e "Current Load Average : $(uptime|grep -o "load average.*"|awk '{print $3" " $4" " $5}')"

#--------Print top 5 most memory consuming resources---------#
printf '\n\e[1;34m%-6s\e[m\n' "Top 5 Memory Resource Hog Processes"
printf '\e[1;34m%-6s\e[m\n' "$D$D"
ps -eo pmem,pcpu,pid,ppid,user,stat,args | sort -k 1 -r | head -6|sed 's/$/\n/'

#--------Print top 5 most CPU consuming resources---------#
printf '\n\e[1;34m%-6s\e[m\n' "Top 5 CPU Resource Hog Processes"
printf '\e[1;34m%-6s\e[m\n' "$D$D"
ps -eo pcpu,pmem,pid,ppid,user,stat,args | sort -k 1 -r | head -6|sed 's/$/\n/'
