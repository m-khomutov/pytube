class Request:
    def __init__(self, data):
        for x in data:
            print(f'{hex(x)}', end=' ')
        print('')

    def reply(self) ->bytes:
        return b''
