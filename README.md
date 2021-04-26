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

**videocodec support**
* h264
* h265

**parameters**
* -p(--port) port to bind(def *4555*)
* -r(--root) files directory(required) - path to seek required mp4 file
* -v(--verb) be verbose (show structure of required mp4 file)
* -h(--help) this help

**installation**

`pip install fragmented-mp4stream-pkg==0.0.2`

**streams**
* json list of available files
  >`http://ip:port/`
* naked fragmented mp4
  >`http://ip:port/filename_without_extension`
* hls container with fragmented mp4
  >`http://ip:port/file_with_m3u_extension`

**example1**

* service
  * python3 mp4stream.py -r ~/video/
* client
  * ffplay http://192.168.250.229:4555/
    >mp4 file list of ~/video/
    ```json
    [
      "MTV.mp4",
      "Wingsuit.mp4",
      "toystory.mp4",
      "nuts720p_4Mb.mp4"
    ]```

**example2**

* service
  * python3 mp4stream.py -r ~/video/
* client
  * ffplay http://192.168.250.229:4555/toystory
    >`~/video/toystory.mp4 - fragmented mp4`


**example3**

* service
  * python3 mp4stream.py -r ~/video/`
* client
  * ffplay http://192.168.250.229:4555/toystory.m3u
    >`~/video/toystory20.mp4 - fragmented mp4 in hls container`
