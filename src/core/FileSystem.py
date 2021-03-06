from . import BitMap
from . import Blocks
from . import BLOCKSIZE
from . import FileTree
from . import File
from . import path
from collections import deque
from math import ceil
import struct

class FileSystem:
	magic=b"\x00\x05\x0a" #05A
	def __newDisk(self,disksize):
		assert disksize!=None
		zeroes=bytes(512)
		for i in range(0,disksize,512):
			self.f.write(zeroes)
		if (disksize%512)!=0:
			self.f.write(zeroes[:disksize%512])
		self.f.seek(0)
		self.f.write(self.magic)
		self.f.write(struct.pack("I",disksize))
		self.f.write(b'\x80')#bitarray([1,0,0,0,0,0,0,0]).tobytes()
		self.f.seek(0)
		
	def __init__(self,filename,disksize=None):
		self.f=open(filename,"r+b")
		temp=self.f.read(len(self.magic))
		if temp==b"":
			self.__newDisk(disksize)
			temp=self.f.read(len(self.magic))
		if temp!=self.magic:
			raise TypeError("Arquivo de formato incorreto")
		self.disksize=struct.unpack("I",self.f.read(4))[0]
		self.blockstotal=self.disksize//BLOCKSIZE
		self.bitmap=BitMap(self.f,(self.f.tell(),self.blockstotal//8))
		offset=ceil(sum(self.bitmap.bitrange)/BLOCKSIZE)
		if len(self.bitmap.allocblocks)==1:self.bitmap.alloc(offset)
		self.blocks=Blocks(self.f,offset,self.blockstotal)

		self.stack=deque([FileTree(self.blocks,0)])
	def get_topdir(self):
		return self.stack[-1]
	def get_root(self):
		return self.stack[0]
	def chdir(self,name):
		if name==".":
			return
		if len(self.stack)!=1:
			if name=="..":
				self.stack.pop()
				return
		todir=self.get_topdir().get(name)
		if todir==None:
			raise FileNotFoundError(name)
		if not todir["isdir"]:
			raise NotADirectoryError(name)
		self.stack.append(FileTree(self.blocks,todir["index"]))
	def pwd(self):
		if len(self.stack)==1:
			return "/"
		return path.join([ft.name for ft in self.stack])
	def mkdir(self,name):
		actdir=self.get_topdir()
		if actdir.get(name)!=None:
			raise FileExistsError(name)
		actdir.add_dir(name,*self.bitmap.alloc(1))
	def newfile(self,name,data_generator,nbytes):
		actdir=self.get_topdir()
		if actdir.get(name)!=None:
			raise FileExistsError(name)
		freeblocks=self.bitmap.alloc(ceil(nbytes/BLOCKSIZE))
		actdir.add_file(name,data_generator,nbytes,freeblocks)
	def rm(self,name):
		actdir=self.get_topdir()
		obj=actdir.get(name)
		if obj==None:
			raise FileNotFoundError(name)
		if obj["isdir"]:
			if len(FileTree(self.blocks,obj["index"]).children)!=0:
				raise OSError("impossível remover diretório não vazio")
			self.bitmap.free([obj["index"]])
		else:
			self.bitmap.free(File.get_all_indexes(self.blocks,obj["index"]))
		actdir.remove(name)
	def cat(self,name):
		actdir=self.get_topdir()
		obj=actdir.get(name)
		if obj==None or obj["isdir"]:
			raise FileNotFoundError(name)
		File.cat(self.blocks,obj["index"])
	def get_file_size(self,name):
		actdir=self.get_topdir()
		obj=actdir.get(name)
		if obj==None or obj["isdir"]:
			raise FileNotFoundError(name)
		return File.get_file_size(self.blocks,obj["index"])
	def cat_block(self,name,n):
		actdir=self.get_topdir()
		obj=actdir.get(name)
		if obj==None or obj["isdir"]:
			raise FileNotFoundError(name)
		return File.cat_block(self.blocks,obj["index"],n)
	def __del__(self):
		self.f.close()



