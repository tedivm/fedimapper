#! /usr/bin/env bash
set -e

# If there's a prestart.sh script in the /app directory or other path specified, run it before starting
PRE_START_PATH=${PRE_START_PATH:-/app/prestart.sh}
echo "Checking for script in $PRE_START_PATH"
if [ -f $PRE_START_PATH ] ; then
    echo "Running prestart script $PRE_START_PATH"
    . "$PRE_START_PATH"
else
    echo "There is no prestart script at $PRE_START_PATH"
fi

PYTHON=$(which python)
COMMAND="$PYTHON -m fedimapper.cli crawl --num-processes=${NUM_PROCESSES:-4}"

echo "System will utilize ${NUM_PROCESSES:-4} nodes for data ingestion and an additional process for management."

if [[ "$RELOAD" == "true" ]]; then
  set -x
  echo "Starting in development mode- ingest will be restarted when files change."
  echo python -m watchfiles --sigint-timeout ${RELOAD_SIGINT_TIMEOUT:-30} "$COMMAND" /app
  python -m watchfiles --sigint-timeout ${RELOAD_SIGINT_TIMEOUT:-30} "$COMMAND" /app/fedimapper
else
  echo $COMMAND
  $COMMAND
fi


