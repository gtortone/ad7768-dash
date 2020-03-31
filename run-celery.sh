#!/bin/bash

source setenv.sh
celery -A sched.tasks worker --loglevel=info --concurrency=1 
