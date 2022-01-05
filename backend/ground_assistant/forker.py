class TheFork:
    def __init__(self, path, pipe_in, pipe_out):
        import os
        from multiprocessing import Process, Pipe
        from threading import Thread, Event

        self.Process = Process
        self.Pipe = Pipe
        self.path = path
        self.pipe_in = pipe_in
        self.pipe_out = pipe_out

        self.plugins = {}
        self.pool = {}
        self.pipes = {}

        self.dstthread = Thread(target=self.distr_center, name="DistributionCenter")
        self.kill = Event()
        self.dstthread.start()

        self.memorypath = path + "/thefork.conf"
        if os.path.exists(self.memorypath):
            memory = open(self.memorypath, "r")
            for line in memory:
                x = line.strip()
                if x[:1] != "#":
                    try:
                        exec(f'import {x} as np\nself.plugins["{x}"] = np\n')
                    except:
                        pass

            memory.close()

        self.memory = open(self.memorypath, "a")

    def distr_center(self):
        while not self.kill.is_set():
            beacon = self.pipe_in.recv()
            try:
                for item in self.pipes:
                    try:
                        self.pipes[item].send(beacon)
                    except BrokenPipeError:
                        self.close(item)
            except RuntimeError as error:
                 print(f'Catched RuntimeError: {error}')
        return

    def register(self, id):
        reserved_keys = ["all"]
        if id in reserved_keys: return f'{id} is not a valid PlugIn name'

        try:
            exec(f'import {id} as np\nif np.mark != "{id}": raise AttributeError\nself.plugins["{id}"] = np')

        except ImportError as ie:
            return str(ie)
        except AttributeError as ae:
            return "PlugIn is not valid"

        else:
            self.memory.write(id + "\n")
            self.memory.flush()
            return f'registered {id}'

    def remove(self, id):
        if not id in self.plugins: return f'{id} is not registered'
        self.close(id)
        self.plugins.pop(id)

        memorydel = open(self.memorypath, "r")
        lines = memorydel.readlines()
        memorydel.close()

        hangover = ""
        memorydel = open(self.memorypath, "w")
        for line in lines:
            if line.strip("\n") != id: memorydel.write(line)
            else: hangover += "\n"
        memorydel.write(hangover)
        memorydel.close()

        return f'removed {id}'

    def load(self, ids):
        ids = [ids]
        if not ids[0] in self.plugins and ids[0] != "all" : return f'{ids[0]} is not registered'
        if ids[0] == "all": ids = self.plugins

        for item in ids:
            if item in self.pool: continue
            p_recv, p_send = self.Pipe()
            self.pool[item] = self.Process(target=self.plugins[item].main, args=(p_recv, self.path,))
            self.pool[item].start()
            self.pipes[item] = p_send
        return f'loaded {ids}'

    def restart(self, id):
        if not id in self.pool and id != "all": return f'{id} is not loaded'
        self.close(id)
        self.load(id)
        return f'restarted {id}'

    def close(self, ids):
        if len(self.pool) == 0: return f'closed {id}'

        if ids == "all": ids = list(self.pool.keys())
        if type(ids) == str: ids = [ids]

        for item in ids:
            if not item in self.pool:
                ids = f'none, {ids[0]} is not loaded'
                continue

            try:
                self.pipe_out.send(f'KILL{item}')
            except:
                pass
            else:
                self.pool[item].join()
            finally:
                self.pipes.pop(item)
                self.pool[item].close()
                self.pool.pop(item)
        return f'closed {ids}'

    def end(self):
        self.close("all")

        self.kill.set()
        self.pipe_out.send("") #If there are no incomming beacons, the loop won't check the event
        if self.dstthread.is_alive(): self.dstthread.join(5)
        if self.dstthread.is_alive(): print("failed joining thread")

        self.memory.flush()
        self.memory.close()
        return "ended"
