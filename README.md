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

**protocol support**
* http(fmp4, hls)
* rtsp

**parameters**
* -p(--ports) ports[http, rtsp] to bind(def. *4555*,*4556*)
* -r(--root) files directory(required) - path to seek required mp4 file
* -s(--segment) segment duration sec.(def. *6*) - floor limit of segment duration
* -c(--cache) cache segmentation - save segmentation as .*.cache files
* -v(--verb) be verbose (show structure of required mp4 file)
* -h(--help) this help

**installation**

`pip install fragmented-mp4stream-pkg==0.0.3`

**subtitles**

* Innner subtitles: track handler=``text``, type=``tx3g``. Verified with ``MPlayer``.
* Outer subtitles: 
  * master playlist: m3u8-file - ex.
  ```m3u
  #EXTM3U
  #EXT-X-MEDIA:TYPE=SUBTITLES,GROUP-ID="subs",NAME="English",DEFAULT=NO,FORCED=NO,URI="http://mkh-Aspire-A315-54K:4555/toystory20sub.m3u8"
  #EXT-X-STREAM-INF:PROGRAM-ID=1,SUBTITLES="subs"
  http://mkh-Aspire-A315-54K:4555/toystory20.m3u8
  ```
  * subtitles playlist: m3u8-file - ex. ``toystory20sub.m3u8``
  ```m3u
    #EXTM3U
    #EXT-X-PLAYLIST-TYPE:VOD
    #EXT-X-MEDIA-SEQUENCE:0
    #EXT-X-TARGETDURATION:8
    #EXTINF:4.0107,
    http://mkh-Aspire-A315-54K:4555/toystory20.vtt
    ```
  * ``webVTT`` subtitles: vtt-files - ex. ``toystory20.vtt``
    ```vtt
    WEBVTT

    00:00:02.829 --> 00:00:4.829 line:74% align:left
    <i>subtitles example.</i>
    ```

**streams**
* json list of available files
  >`http://ip:http_port/`
* fragmented mp4
  >`http://ip:http_port/filename_without_extension`
* hls container with fragmented mp4
  >`http://ip:http_port/filename_with_m3u_extension`
* rtsp
  >`rtsp://ip:rtsp_port/filename_without_extension`

**example1**

* service
  * python3 mp4stream.py -r ~/video/
* client
  * ffplay http://192.168.250.229:4555/
    >mp4 file list of ~/video/
    ```json
    [
      "MTV",
      "Wingsuit",
      "toystory",
      "nuts720p_4Mb"
    ]
    ```

**example2**

* service
  * python3 mp4stream.py -r ~/video/
* client
  * ffplay http://192.168.250.229:4555/toystory
    >`~/video/toystory.mp4 - fragmented mp4`


**example3**

* service
  * python3 mp4stream.py -r ~/video/
* client
  * ffplay http://192.168.250.229:4555/toystory.m3u
    >`~/video/toystory20.mp4 - fragmented mp4 in hls container`

**example4**

* service
  * python3 mp4stream.py -r ~/video/
* client
  * ffplay -rtsp_transport tcp rtsp://192.168.250.229:4556/toystory
    >`~/video/toystory.mp4 - rtsp stream`
