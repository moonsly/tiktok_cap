#!/bin/bash

rm ./solved/*

curl -X POST -H "Content-Type: multipart/form-data"  -F 'file=@cap1.jpg' -F "api_id=0x52837abc348d3f8252826abde426262324" http://127.0.0.1:18757/solve

curl -X POST -H "Content-Type: multipart/form-data"  -F 'file=@cap2.jpg' -F "api_id=0x52837abc348d3f8252826abde426262324" http://127.0.0.1:18757/solve

curl -X POST -H "Content-Type: multipart/form-data"  -F 'file=@cap3.jpg' -F "api_id=0x52837abc348d3f8252826abde426262324" http://127.0.0.1:18757/solve

curl -X POST -H "Content-Type: multipart/form-data"  -F 'file=@cap4.jpg' -F "api_id=0x52837abc348d3f8252826abde426262324" http://127.0.0.1:18757/solve

curl -X POST -H "Content-Type: multipart/form-data"  -F 'file=@cap5.jpg' -F "api_id=0x52837abc348d3f8252826abde426262324" http://127.0.0.1:18757/solve
