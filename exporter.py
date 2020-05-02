from prometheus_client import make_wsgi_app
from prometheus_client.exposition import _SilentHandler
from prometheus_client.core import GaugeMetricFamily, CounterMetricFamily, StateSetMetricFamily, REGISTRY
from wsgiref.simple_server import make_server
import requests
import os

STREAM_LABELS = ['server', 'stream', 'id', 'vhost', 'app']
VIDEO_CODEC_ENUM = ['h264']


class StreamCollector(object):
    def collect(self):
        base_url = '%s://%s:%s' % (
                os.environ.get('SRS_API_SCHEME', 'http'),
                os.environ.get('SRS_API_HOST', 'localhost'),
                os.environ.get('SRS_API_PORT', 1985)
        )
        r_streams = requests.get('%s/api/v1/streams/' % base_url)
        streams = r_streams.json()

        metrics = {}
        metrics['total'] = GaugeMetricFamily('stream_active_total', 'Total amount of active streams', labels=['server'])
        metrics['clients'] = GaugeMetricFamily('stream_clients', 'connected clients', labels=STREAM_LABELS)
        metrics['live_ms'] = CounterMetricFamily('stream_live_ms', 'mystery stat', labels=STREAM_LABELS)
        metrics['recv_bytes'] = CounterMetricFamily('stream_recv_bytes', 'received bytes', labels=STREAM_LABELS)
        metrics['sent_bytes'] = CounterMetricFamily('stream_sent_bytes', 'sent bytes', labels=STREAM_LABELS)
        metrics['frames'] = CounterMetricFamily('stream_frames', 'sent frames', labels=STREAM_LABELS)
        metrics['video_codec'] = StateSetMetricFamily('stream_video_codec', 'video codec', labels=STREAM_LABELS)
        metrics['video_width'] = GaugeMetricFamily('stream_video_width', 'video width', labels=STREAM_LABELS)
        metrics['video_height'] = GaugeMetricFamily('stream_video_height', 'video height', labels=STREAM_LABELS)

        metrics['total'].add_metric([str(streams.get('server'))], len(streams.get('streams')))

        for stream in streams.get('streams', []):
            lvals = [
                str(streams.get('server')),
                str(stream.get('name')),
                str(stream.get('id')),
                str(stream.get('vhost')),
                str(stream.get('app'))
            ]
            metrics['clients'].add_metric(lvals, stream.get('clients'))
            metrics['live_ms'].add_metric(lvals, stream.get('live_ms'))
            metrics['recv_bytes'].add_metric(lvals, stream.get('recv_bytes'))
            metrics['sent_bytes'].add_metric(lvals, stream.get('send_bytes'))  # sic
            metrics['frames'].add_metric(lvals, stream.get('frames'))
            vstates = dict(zip(VIDEO_CODEC_ENUM + ['unknown'], [False] * (1 + len(VIDEO_CODEC_ENUM))))
            if stream.get('video'):
                v = stream.get('video')
                codec = v.get('codec').lower()

                metrics['video_width'].add_metric(lvals, v.get('width', 0))
                metrics['video_height'].add_metric(lvals, v.get('height', 0))

                if codec in VIDEO_CODEC_ENUM:
                    vstates[codec] = True
            else:
                vstates['unknown'] = True

            metrics['video_codec'].add_metric(lvals, vstates)

        for metric in metrics:
            yield metrics[metric]


if __name__ == '__main__':
    REGISTRY.register(StreamCollector())

    app = make_wsgi_app()
    httpd = make_server('', int(os.environ.get('LISTEN_PORT', 9185)), app, handler_class=_SilentHandler)
    httpd.serve_forever()
