#!/bin/bash
export NODE_OPTIONS="--dns-result-order=ipv4first"
exec next dev -p 3000
