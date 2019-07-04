import time, random, threading, requests
import csmapi

class DAN():

    def __init__(self):
        self.MAC = self.get_mac_addr()

    # example
    profile = {
    #    'd_name': None,
        'dm_name': 'MorSensor',
        'u_name': 'yb',
        'is_sim': False,
        'df_list': ['Acceleration', 'Temperature'],
    }
    mac_addr = None

    state = 'SUSPEND'     #for control channel
    #state = 'RESUME'

    SelectedDF = []
    def ControlChannel(self):
        print('Device state:', self.state)
        NewSession=requests.Session()
        control_channel_timestamp = None
        while True:
            time.sleep(2)
            try:
                self.CH = csmapi.pull(self.MAC,'__Ctl_O__', NewSession)
                if self.CH != []:
                    if control_channel_timestamp == self.CH[0][0]: continue
                    control_channel_timestamp = self.CH[0][0]
                    cmd = self.CH[0][1][0]
                    if cmd == 'RESUME':  
                        print('Device state: RESUME.') 
                        self.state = 'RESUME'
                    elif cmd == 'SUSPEND': 
                        print('Device state: SUSPEND.') 
                        self.state = 'SUSPEND'
                    elif cmd == 'SET_DF_STATUS':
                        csmapi.push(self.MAC,'__Ctl_I__',['SET_DF_STATUS_RSP',{'cmd_params':self.CH[0][1][1]['cmd_params']}], NewSession)
                        DF_STATUS = list(self.CH[0][1][1]['cmd_params'][0])
                        self.SelectedDF = []
                        index=0            
                        self.profile['df_list'] = csmapi.pull(self.MAC, 'profile')['df_list']              #new
                        for STATUS in DF_STATUS:
                            if STATUS == '1':
                                self.SelectedDF.append(self.profile['df_list'][index])
                            index=index+1
            except Exception as e:
                print ('Control error:', e)
                if str(e).find('mac_addr not found:') != -1:
                    print('Reg_addr is not found. Try to re-register...')
                    self.device_registration_with_retry()
                else:
                    print('ControlChannel failed due to unknow reasons.')
                    time.sleep(1)    

    def get_mac_addr(self):
        from uuid import getnode
        mac = getnode()
        mac = ''.join(("%012X" % mac)[i:i+2] for i in range(0, 12, 2))
        return mac

    def detect_local_ec(self):
        EASYCONNECT_HOST=None
        import socket
        UDP_IP = ''
        UDP_PORT = 17000
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((UDP_IP, UDP_PORT))
        while EASYCONNECT_HOST==None:
            print ('Searching for the IoTtalk server...')
            data, addr = s.recvfrom(1024)
            if str(data.decode()) == 'easyconnect':
                EASYCONNECT_HOST = 'http://{}:9999'.format(addr[0])
                csmapi.ENDPOINT=EASYCONNECT_HOST
                #print('IoTtalk server = {}'.format(csmapi.ENDPOINT))

    timestamp={}
    thx=None
    def register_device(self, addr):
        if csmapi.ENDPOINT == None: detect_local_ec()

        if addr != None: self.MAC = addr

        for i in self.profile['df_list']: self.timestamp[i] = ''

        print('IoTtalk Server = {}'.format(csmapi.ENDPOINT))
        self.profile['d_name'] = csmapi.register(self.MAC,self.profile)
        print ('This device has successfully registered.')
        print ('Device name = ' + self.profile['d_name'])
            
        if self.thx == None:
            print ('Create control threading')
            self.thx=threading.Thread(target=self.ControlChannel)     #for control channel
            self.thx.daemon = True                               #for control channel
            self.thx.start()                                     #for control channel 


    def device_registration_with_retry(self, URL=None, addr=None):
        if URL != None:
            csmapi.ENDPOINT = URL
        success = False
        while not success:
            try:
                self.register_device(addr)
                success = True
            except Exception as e:
                print ('Attach failed: '),
                print (e)
            time.sleep(1)

    def pull(self, FEATURE_NAME):
        if self.state == 'RESUME': data = csmapi.pull(self.MAC,FEATURE_NAME)
        else: data = []
            
        if data != []:
            if self.timestamp[FEATURE_NAME] == data[0][0]:
                return None
            self.timestamp[FEATURE_NAME] = data[0][0]
            if data[0][1] != []:
                return data[0][1]
            else: return None
        else:
            return None

    def push(self, FEATURE_NAME, *data):
        if self.state == 'RESUME':
            return csmapi.push(self.MAC, FEATURE_NAME, list(data))
        else: return None

    def get_alias(self, FEATURE_NAME):
        try:
            alias = csmapi.get_alias(self.MAC,FEATURE_NAME)
        except Exception as e:
            #print (e)
            return None
        else:
            return alias

    def set_alias(self, FEATURE_NAME, alias):
        try:
            alias = csmapi.set_alias(self.MAC, FEATURE_NAME, alias)
        except Exception as e:
            #print (e)
            return None
        else:
            return alias

            
    def deregister(self):
        return csmapi.deregister(self.MAC)
