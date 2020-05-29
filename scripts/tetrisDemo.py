# coding:utf-8
import random
import maya.cmds as cmds
import maya.mel as mel

'''
TODO
- 回転時の押し出し
- 回転の中心点を調整
- スコア表示
'''

#---------------- Main --------------------

w,h = 10,20
spownPos = [5,18]

minos = [
		[[0,1],[0,-1],[0,-2]],	#I (id=0)
		[[1,0],[1,-1],[0,-1]],	#O (id=1)
		[[0,1],[1,1],[-1,0]],	#S (id=2)
		[[0,1],[-1,1],[1,0]],	#Z (id=3)
		[[0,1],[0,-1],[-1,-1]],	#J (id=4)
		[[0,1],[0,-1],[1,-1]],	#L (id=5)
		[[0,1],[-1,0],[1,0]]	#T (id=6)
]

class Singleton(object):
	@classmethod
	def get_instance(cls, input):
		if not hasattr(cls, "_instance"):
			cls._instance = cls(input)
		else:
			cls._instance.input = input
		return cls._instance
		
class Tetris(Singleton):
	def __init__(self):
		self.bo =  [[-1]*h for i in range(w)]	#screen borad
		self.preBo =  [[-2]*h for i in range(w)]	#off screen borad
		self.playerPos = list(spownPos)
		self.playerMino = [[None,None]]*3
		self.playerMinoNum = 0
		self.minoRand = self.createMinoRand()
		self.timer = 0
		self.timerLevel = 20
		self.isContact = False
		self.gameOverCount = 100
		self.rec = {}
		self.recLen = 0
			
		cmds.undoInfo(st=False)
		cmds.currentUnit(t='ntsc')
		cmds.playbackOptions(e=1,playbackSpeed=0,maxPlaybackSpeed=1)
		cmds.evaluationManager(mode='off')
		#cmds.evaluationManager(inv=True)
		cmds.playbackOptions(min=1,max=5000)
		self.createObjs()

	def gameStart(self,speed,recLen):
		self.timerLevel = int(20/speed)
		
		cmds.currentTime(1)
		self.gameOverCount = -1
		self.recLen = recLen
		self.rec = {}
		for x in range(w):
			for y in range(h):
				coreName = '_'+str(x)+'_'+str(y)
				self.rec[coreName] = [1.0]*recLen
		self.spown()	
		cmds.play(forward=1)
		
	
	def createMinoRand(self):
		cnt = [7]
		minoRandList = range(7)
		def inner():
			cnt[0] += 1
			if(cnt[0]>6):
				minoRandList[:] = random.sample(range(7),7)
				cnt[0] = 0
			return minoRandList[cnt[0]]
		return inner	
	
	def createObjs(self):
		#Materials
		matCols = [
			[0,1,1],
			[1,1,0],
			[0,1,0],
			[1,0,0],
			[0,0,1],
			[1,0.5,0],
			[1,0,1]
		]
		for num in range(7):
			name = 'mino_'+str(num)+'_mat'
			if not cmds.objExists(name+'SG'):
				cmds.sets(n=name+'SG',renderable=1,noSurfaceShader=1,empty=1)
			if not cmds.objExists(name):
				cmds.shadingNode('lambert',asShader=1,n=name)
				cmds.setAttr(
					name+'.color',
					matCols[num][0],matCols[num][1],matCols[num][2],
					type='double3'
				)
				cmds.connectAttr(name+'.outColor',name+'SG.surfaceShader',f=1)
	
		#Anim for force evaluation 
		if(not cmds.objExists('dummyAnim')):
			cmds.createNode('animCurveTU',name='dummyAnim')
			cmds.setAttr('dummyAnim.postInfinity',3)
			cmds.setKeyframe('dummyAnim',t=0,v=1)
			cmds.setKeyframe('dummyAnim',t=1,v=1.0001)
		
		#borad		
		for x in range(w):
			for y in range(h):
				coreName = '_'+str(x)+'_'+str(y)
				for c in range(7):
					name = 'c'+str(c)+coreName
					sgName = 'mino_'+str(c)+'_matSG'
					if not cmds.objExists(name):
						cmds.polyCube(n=name,w=0.95,d=0.95,h=0.95)
						cmds.setAttr('.t',x,y,0)
						cmds.sets(name,e=1,fe=sgName)
					cmds.connectAttr('dummyAnim.o',name+'.sz',f=1)
	
		#controllers
		if not cmds.objExists('b_left'):
			cmds.group(em=1,n='b_left')
			cmds.group(n='b_up')
			cmds.group(em=1,n='b_down')
			cmds.group(n='neutral',parent='b_up')
			cmds.group(em=1,n='b_right',parent='b_up')
	
		#expression
		if not cmds.objExists('input_exp'):
			cmds.expression(
				n =	'input_exp',
				s =	"neutral.translateX=0;\nstring $sels[]=`ls -sl`;\n"+
					"python (\"t.tetObj.update('\"+$sels[0]+\"')\");\nselect -r neutral;",
				o =	'right',ae=1,uc='all'
			)
		
	def draw(self):
		def setBlock(x=0,y=0,val=1):
			if(not self.isIndexRange(x,y)):
				return
			coreName = '_'+str(x)+'_'+str(y)
			if(not val==self.preBo[x][y]):		
				for c in range(7):
					name = 'c'+str(c)+coreName
					_val = 1 if val==c  else 0			
					cmds.setAttr(name+'.sx',_val)
					cmds.setAttr(name+'.sy',_val)
			self.preBo[x][y] = val
			t = int(cmds.currentTime(query=True))
			if(0<t<self.recLen):
				self.rec[coreName][t]=val
	
		#borad
		for x in range(w):
			for y in range(h):
				setBlock(x,y,self.bo[x][y])
				
		#player
	
		if(self.gameOverCount==-1):
			setBlock(self.playerPos[0],self.playerPos[1],self.playerMinoNum)
			for n in range(3):
				setBlock(
					self.playerPos[0]+self.playerMino[n][0],
					self.playerPos[1]+self.playerMino[n][1],
					self.playerMinoNum
				)
	
	def spin(self,a2d):
		result = []
		for n in range(3):
			result.append([a2d[n][1],-a2d[n][0]])
		return result
	
	def test(self,_playerPos,__playerMino):
		_playerMino = __playerMino+[[0,0]]	#__playerMino3マス、原点の[0,0]の1マスを合わせた配列
		for n in range(4):
			x = _playerPos[0]+_playerMino[n][0]
			y = _playerPos[1]+_playerMino[n][1]
			if ( not(x in range(w)) or y<0 ):
				return False
			if ( self.isIndexRange(x,y) ):
				if self.bo[x][y]!=-1:
					return False
		return True
	
	def isIndexRange(self,x,y):
		return (x in range(w) and y in range(h))
		
	def spown(self):
		self.playerPos[:] = list(spownPos)
		self.playerMinoNum = self.minoRand()
		del self.playerMino[:]
		for m in minos[self.playerMinoNum]:
			self.playerMino.append([m[0],m[1]])
		return self.test(self.playerPos,self.playerMino)
	
	def put(self):
		for n in range(3):
			x = self.playerPos[0]+self.playerMino[n][0]
			y = self.playerPos[1]+self.playerMino[n][1]
			if(self.isIndexRange(x,y)):
				self.bo[x][y] = self.playerMinoNum
		if(self.isIndexRange(self.playerPos[0],self.playerPos[1])):
			self.bo[self.playerPos[0]][self.playerPos[1]] = self.playerMinoNum
	
	def breakLine(self):
		cLines = []
		for y in range(h):
			cFlag = True
			for x in range(w):
				if self.bo[x][y]==-1:
					cFlag = False
			if cFlag:
				cLines.append(y)
				self.timerLevel = max(1,self.timerLevel-1)
		for y in cLines[::-1]:
			for x in range(w):
				self.bo[x].pop(y)
				self.bo[x].append(-1)
	
	def update(self,key):
		#key
		if key=='b_up':
			if self.test(self.playerPos,self.spin(self.playerMino)):
				self.playerMino = self.spin(self.playerMino)
		if key=='b_left':
			if self.test([self.playerPos[0]-1,self.playerPos[1]],self.playerMino):
				self.playerPos[0] -= 1			
		if key=='b_right':
			if self.test([self.playerPos[0]+1,self.playerPos[1]],self.playerMino):
				self.playerPos[0] += 1
		if key=='b_down':
			for lev in range(h):
				if not self.test([self.playerPos[0],self.playerPos[1]-lev],self.playerMino):
					self.playerPos[1] -= lev-1
					self.isContact = True
					self.timer = 20
					break
		#fall
		if self.gameOverCount<0:
			if self.timer==0:
				if self.test([self.playerPos[0],self.playerPos[1]-1],self.playerMino):
					self.playerPos[1] -= 1
		
				else:
					if self.isContact:
						self.put()
						self.isContact = False
						self.breakLine()
						if not self.spown():
							self.gameOverCount = 0
					else:
						self.isContact = True
		else:
			if self.gameOverCount<h:
				for x in range(w):
					self.bo[x][self.gameOverCount] = 1
				self.gameOverCount += 1
	
		self.draw()
		self.timer = (self.timer+1)%self.timerLevel
		cmds.setFocus('MayaWindow')
		#cmds.setFocus(cmds.getPanel(type='modelPanel')[-1])
		
	def bakeReplay(self):
		def setBlockKey(time=0,coreName='_0_0',col=0,vis=1,single=False):
			name = 'c'+str(col)+coreName
			for attr in ['sx','sy']:
				cmds.setKeyframe(name+'.'+attr,t=t,v=vis,ott='step')
				if not single:
					cmds.setKeyframe(name+'.'+attr,t=t-0.1,v=int(not vis),ott='step')	
		for x in range(w):
			for y in range(h):
				coreName = '_'+str(x)+'_'+str(y)
				for t in range(1,self.recLen):
					if(t<=2):
						for c in range(7):
							setBlockKey(1,coreName,c,1,True)
							setBlockKey(2,coreName,c,0,True)
					else:
						preVal = self.rec[coreName][t-1]
						val = self.rec[coreName][t]
						if(val==preVal):
							continue
						if(not val==-1):
							setBlockKey(t,coreName,val,1)
						if(not preVal==-1):
							setBlockKey(t,coreName,preVal,0)
		cmds.delete('input_exp','dummyAnim')


#----------------- UI -------------------

tetObj = None

def show():
	global tetObj
	tetObj = Tetris()
	cmds.window('tetris_win',w=400,title='Tetris Demo')
	cmds.columnLayout(adj=1)
	cmds.intFieldGrp('rec_IF',l=u'Rec Dur(f)',v1=1000)
	cmds.floatFieldGrp('speed_FF',l=u'Speed',v1=1)
	cmds.button(
		u'Reset',
		w=70,h=24,
		c=lambda a:tetObj.__init__()
	)
	cmds.button(
		u'Game Start',
		w=70,h=24,bgc=(0.1,0.27,0.47),
		c=lambda a:
			tetObj.gameStart(
				cmds.floatFieldGrp('speed_FF',q=1,v1=1),
				cmds.intFieldGrp('rec_IF',q=1,v1=1)
			)
	)
	cmds.button(
		u'Replay (Bake)',
		w=70,h=24,
		c=lambda a:tetObj.bakeReplay()
	)
	cmds.window('tetris_win', edit=True, vis=True)