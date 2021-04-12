# Fragmented mp4stream Package

**Usage**
```python 
import fragmentedmp4stream.service
import sys

def main(argv):
    fragmentedmp4stream.service.start(argv)

if __name__ == "__main__":
    main(sys.argv[1:])
```

**parameters**
* -p(--port) port to bind(def *4555*)
* -r(--root) files directory(required) - path to seek required mp4 file
* -v(--verb) be verbose (show structure of required mp4 file)
* -h(--help) this help

**installation**

`pip install fragmented-mp4stream-pkg==0.0.1`

**url**

`http://ip:port/file_without_extension`

**example**

* service
>`python3 mp4stream.py -r ~/video/`
* client
>`ffplay http://192.168.250.229:4555/toystory20`

Service streams ~/video/toystory20.mp4
