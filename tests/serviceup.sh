#! /bin/bash
#
# Description:
# Check if service is up
#

SERVICE=$1
COUNT=1
MAXCOUNT=20

docker service ps $SERVICE --format "{{.CurrentState}}" 2>/dev/null | grep Running
service_up=$?

until [ $service_up -eq 0 ]; do
    echo "$COUNT: service $SERVICE unavailable"
    sleep 5
    docker service ps $SERVICE --format "{{.CurrentState}}" 2>/dev/null | grep Running
    service_up=$?
    if [ $COUNT -eq $MAXCOUNT ]; then
	echo "service $SERVICE not found; giving up"
	exit 1
    fi
    COUNT=$((COUNT+1))
done

echo "service $SERVICE up!"

exit 0
