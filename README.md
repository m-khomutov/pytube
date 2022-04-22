# pytube Package

**Installation**

`pip install pytube-pkg==0.0.1`

**Usage**

`pytube parameters`

**parameters**
* -p(--ports) ports[http,https,rtsp] to bind(def. *4555*,*4556*,*4557*)
* -r(--root) files directory(required) - path to seek required mp4 file
* -s(--segment) segment duration sec.(def. *6*) - floor limit of segment duration
* -c(--cache) cache segmentation - save segmentation as .*.cache files
* -b(--basic) user:password@realm (use Basic Authorization)
* -d(--digest) user:password@realm (use Digest Authorization)
* -k(--keys) directory with key.pem and cert.pem files (req. for https)
* -v(--verb) be verbose (show structure of required mp4 file)
* -h(--help) this help


**videocodecs**
* h264
* h265

**protocols**
* http[s](fMP4, HLS, MPEG-dash)
* rtsp(tcp rtp-interleaved)

**subtitles**

* Inner subtitles: track handler=``text``, type=``tx3g``. Verified with ``MPlayer``.
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
  >`http[s]://ip:http[s]_port/`
* fragmented mp4
  >`http[s]://ip:http[s]_port/filename_without_extension`
* HLS with fragmented mp4
  >`http[s]://ip:http[s]_port/filename_with_m3u[8]_extension`
* MPEG-dash with fragmented mp4 (multiplexed)
  >`http[s]://ip:http[s]_port/filename_with_mpd_extension`
* rtsp
  >`rtsp://ip:rtsp_port/filename_without_extension`

**authorization**

Supports Basic and Digest authorization (specific or both).

**rtsp stream**

Supports trick play:
* reverse
* scaling
* seeking

Supports parameters
* position - returns asset position timestamp 

**example1**

* service
  * pytube -r ~/video/
* client
  *  curl --request GET http://192.168.250.229:4555/ | jq .
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
  * pytube -r ~/video/
* client
  * ffplay http://192.168.250.229:4555/toystory
    >`~/video/toystory.mp4 - fragmented mp4`


**example3**

* service
  * pytube -r ~/video/
* client
  * ffplay http://192.168.250.229:4555/toystory.m3u
    >`~/video/toystory.mp4 - HLS with fragmented mp4`

**example4**

* service
  * pytube -r ~/video/ -k ssl
* client
  * vlc https://192.168.250.229:4556/toystory.mpd
    >`~/video/toystory.mp4 - MPEG_dash with fragmented mp4`

**example5**

* service
  * pytube -r ~/video/
* client
  * ffplay -rtsp_transport tcp rtsp://192.168.250.229:4557/toystory
    >`~/video/toystory.mp4 - rtsp stream`
