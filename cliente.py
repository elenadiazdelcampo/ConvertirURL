#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys

import Ice
Ice.loadSlice('downloader.ice')
import time
import Downloader
import binascii


BLOCK_SIZE = 10240


def receive(transfer, destination_file):
    with open(destination_file, 'wb') as file_contents:
        remoteEOF = False
        while not remoteEOF:
            data = transfer.recv(BLOCK_SIZE)
            # Remove additional byte added by str() at server
            if len(data) > 1:
                data = data[1:]
            data = binascii.a2b_base64(data)
            remoteEOF = len(data) < BLOCK_SIZE
            if data:
                file_contents.write(data)
        transfer.end()

class Manejador(Ice.Application):
    def __init__(self):
        self.disponibles = {}

    def addDownloader(self, name, proxy, current=None):
        self.disponibles[name] = proxy
        
    def descargarYoutube(self, name, url, current=None):     
        wait = self.disponibles[name].addDownloadTaskAsync(url)
        while wait.running():
            print('espera...')
            time.sleep(1.5)
            if wait.done():
                print('Hecho!')


    def mostrarCanciones(self, name, current=None):
        wait = self.disponibles[name].getSongListAsync()
        while wait.running():
            print('espera...')
            time.sleep(1.5)
            if wait.done():
                print('Hecho!')
                vect= wait.result()
                for cancion in vect:
                    print(cancion)        
       
    def transferirSong(self, name, song_name, current=None):
        wait = self.disponibles[name].getAsync(song_name)
        while wait.running():
            print('espera...')
            time.sleep(1.5)
            if wait.done():
                print('Hecho!')
                transfer= wait.result()
        receive(transfer, song_name)

    def eliminarDownloader(self, name, current=None):
        del self.disponibles[name]

class Client(Ice.Application):
    def __init__(self):
        self.n = 0
        self.gestor = Manejador()
        self.factory = None

    def prepareFactory(self, factory, current=None):
        self.factory = factory

    def transferirCancion(self, current=None):
        name = self.in_str('Introduzca el nombre del servidor que utilizara\n')
        self.gestor.mostrarCanciones(name)
        song_name = self.in_str('Introduzca el nombre de la cancion que prefiera\n')
        self.gestor.transferirSong(name,song_name)
        print('Solicitado!')

    def descargarCancion(self, current=None):
        name = self.in_str('Introduzca el nombre del servidor que utilizara\n')
        self.gestor.mostrarCanciones(name)
        url = self.in_str('Introduzca el enlace de descarga\n')
        self.gestor.descargarYoutube(name,url)
        print('Solicitado!')

    def eliminarServer(self, current=None):
        name = self.in_str('Introduzca el nombre del servidor que quiere eliminar\n')
        try:
            self.factory.kill(name)
            self.gestor.eliminarDownloader(name)
            return True
        except Downloader.SchedulerNotFound:
            print('Error: El servidor no se ha localizado')
            return False

    def crearServer(self, current=None):
        name = self.in_str('Introduzca el nombre del servidor\n')
        try:
            server = self.factory.make(name)
            self.gestor.addDownloader(name, server)
            return True
        except Downloader.SchedulerAlreadyExists:
            print('Error: El servidor ya existe')
            return False

    def principal(self, current=None):
        print('\nSeleccione la opcion que desees')
        print('1. Transferir cancion')
        print('2. Descargar cancion')
        print('3. Crear Downloader')
        print('4. Eliminar Downloader') 
        print('5. Downloades Disponibles')
        print('6. Salir')

    def Menu(self, opcion, current=None):
        if opcion == 1:
            if self.n == 0:
                print('Debe crear antes un Servidor')
            else:
                self.transferirCancion()
        elif opcion == 2:
            if self.n == 0:
                print('Debe crear antes un Servidor')
            else:
                self.descargarCancion()
        elif opcion == 3:
            if self.crearServer():
                self.n = self.n + 1
        elif opcion == 4:
            if self.n == 0:
                print('Debe crear antes un Servidor')
            else:
                if self.eliminarServer():
                    self.n = self.n - 1
        elif opcion == 5:
            print('Numero de servidores creados: {}'.format(self.factory.availableSchedulers()))
        elif opcion == 6:
            print('Adios')
        else:
            print('Introduzca una opcion valida')

    def in_str(self, text, current=None):
        opt = input(text)
        return opt

    def in_int(self, text, current=None):
        opt = int(input(text))
        return opt

    def run(self, argv):   
        print('%%%%%%%%%%%%CLIENTE%%%%%%%%%%%%%')
        proxy = self.communicator().stringToProxy(argv[1])
        factory = Downloader.SchedulerFactoryPrx.checkedCast(proxy)
        if not factory:
            raise RuntimeError('Invalid factory proxy')
        self.prepareFactory(factory)
        opcion = 0
        while opcion != 6:
            self.principal()
            opcion = self.in_int("")
            self.Menu(opcion)
        
        return 0

sys.exit(Client().main(sys.argv))
