# Auteur : [Flobul](https://github.com/Flobul/conso_veolia) and some modif from [JohanSweck] (https://github.com/JohanSweck/conso_veolia)
#
# Modif : [Aegis](https://github.com/Aegis940/plugin-teleo) pour intégration au plugin teleo

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait # available since 2.4.0
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from pyvirtualdisplay import Display

import os
import sys
import time
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

# URL des pages nécessaires
url = 'https://espace-client.vedif.eau.veolia.fr'
urlHome = url + '/s/login/'
urlConso = url + '/s/historique'
urlConsoMultiContrat = url + '/s/contrats'

browser = None
display = None
chromedriverLog = None
logger = None
logLevel = None

def take_screenshot(name,tempDir):
	if (logLevel != logging.DEBUG) : return;
	
	logging.debug("Taking screenshot : %s"%name)
	screenshot = tempDir + '/' + name
	
	browser.save_screenshot('%s.png'%screenshot)

def setLogLevel(level):
	if (level == '100') : return logging.DEBUG
	if (level == '200') : return logging.INFO
	if (level == '300') : return logging.WARNING
	if (level == '400') : return logging.ERROR
	if (level == '1000') : return logging.CRITICAL
	
	return logging.INFO
	
def initLogger(logFile, logLevel):
	logger.setLevel(logLevel)
	formatter = logging.Formatter('[%(asctime)s][%(levelname)s] : [Script Python] %(message)s')
	file_handler = RotatingFileHandler(logFile, 'a', 1000000, 1)
	
	file_handler.setLevel(logLevel)
	file_handler.setFormatter(formatter)
	logger.addHandler(file_handler)
	
	if (sys.argv == 4):
		steam_handler = logging.StreamHandler()
		steam_handler.setLevel(logLevel)
		steam_handler.setFormatter(formatter)
		logger.addHandler(steam_handler)
		
def waitData(exitCond, sleepTime, loopNb):

	kpi_field = browser.find_elements(By.XPATH, '//*[@class="kpi-value"]')

	nb_kpi = len(kpi_field)
	if nb_kpi != 3 : raise Exception('wrong KPI number')
	
	loop = 1
	while True:
		time.sleep(sleepTime)
		
		if (kpi_field[2].text.find(exitCond) != -1): break

		if (loop > loopNb): raise Exception('display data too long')
		loop = loop + 1
	
	logger.debug(kpi_field[2].text + ' waitTime = ' + str(loop*sleepTime) + ' sec')	
	
try:
	returnStatus = 0

	if len( sys.argv ) < 4:
		sys.exit(returnStatus)
		
	#Configuration des logs
	tempDir = os.path.normpath(sys.argv[3])
	
	#logPath = '/var/www/html/log'
	#if (os.path.exists(logPath)) : logFile = logPath + '/teleo_python'
	#else : logFile = tempDir + '/teleo_python.log'	
	logFile = tempDir + '/teleo_python.log'
	
	chromedriverLog = tempDir + '/chromedriver.log'
	
	Path(tempDir).mkdir(mode=0o777,parents=True, exist_ok=True)

	logger = logging.getLogger()
	
	if len( sys.argv ) >= 5: logLevel = setLogLevel(sys.argv[4])
	else: logLevel = logging.INFO

	initLogger(logFile, logLevel)

	#Informations de connexion
	veolia_login = sys.argv[1]
	veolia_password = sys.argv[2]

	#Emplacement de sauvegarde du fichier à télécharger
	downloadPath = os.path.normpath(sys.argv[3])
	downloadFile = downloadPath + '/historique_jours_litres.csv'
	
	#Démarre l'affichage virtuel
	display = Display(visible=0, size=(800, 600))
	display.start()

	options = webdriver.ChromeOptions()
	options.headless = True

	prefs = {"download.default_directory" : downloadPath}
	options.add_experimental_option("prefs",prefs)

	#Démarrage du browser Chrome 
	logger.info('Initialisation browser')
	browser = webdriver.Chrome(options=options, service_args=["--verbose", "--log-path=" + chromedriverLog])

	# Page de login
	logger.info('Page de login')
	browser.get(urlHome)
	time.sleep(3)
	wait = WebDriverWait(browser, 20)
	wait.until(EC.presence_of_element_located((By.XPATH, "//input[@id='input-3']")))
	nb_form = len(browser.find_elements(By.XPATH, "//input[@inputmode='email']"))
	time.sleep(3)
	if nb_form != 2 : raise Exception('wrong login number')

	# Recherche et remplis les champs d'identification
	idEmail = browser.find_element(By.XPATH, "//input[@id='input-3']")
	idPassword = browser.find_element(By.XPATH, "//input[@type='password']")

	idEmail.clear()
	idEmail.send_keys(veolia_login)
	time.sleep(3)

	idPassword.clear()
	idPassword.send_keys(veolia_password)
	time.sleep(3)

	take_screenshot("1_login_form",tempDir)
	
	loginButton = browser.find_element(By.CLASS_NAME, 'submit-button')
	loginButton.click()
	time.sleep(5)

	take_screenshot("2_login_form",tempDir)
	
	# Manage Multi-Contract
	if len( sys.argv ) == 6 :
		contractID = sys.argv[5]
		
		# Page des contrats
		logger.info('Page de(s) contrat(s)')
		browser.get(urlConsoMultiContrat)
		WebDriverWait(browser, 30).until(EC.presence_of_element_located((By.XPATH, "//a[contains(.," + contractID +")]")))

		take_screenshot("2_contrats",tempDir)
		
		# Page de consommation
		logger.info('Page de consommation')

		contract=browser.find_element(By.XPATH, "//a[contains(.," + contractID +")]")
		contract.click()

		WebDriverWait(browser, 30).until(EC.presence_of_element_located((By.XPATH, "//span[contains(.,'Historique')]//parent::div//parent::a")))
		
		take_screenshot("2_contrat_selected",tempDir)
		
		histoTab = browser.find_element(By.XPATH, "//span[contains(.,'Historique')]//parent::div//parent::a")
		histoTab.click()
	
		take_screenshot("3a_conso",tempDir)
	
	else : 
		# Page de consommation
		logger.info('Page de consommation')
		
		browser.get(urlConso)

	WebDriverWait(browser, 60).until(EC.presence_of_element_located((By.XPATH , "//input[@name='from']")))

	# On attend que les premières données soient chargées
	waitData("mois",5,4)
	
	# Sélection boutons
	logger.info('Sélection des données en Jours et Litres')
	
	dayButton = browser.find_element(By.XPATH, "//span[contains(.,'Jours')]//parent::button")
	dayButton.send_keys(Keys.RETURN)
	waitData("jour",3,5)
	
	literButton = browser.find_element(By.XPATH, "//span[contains(.,'Litres')]//parent::button")
	literButton.send_keys(Keys.RETURN)
	waitData("Litres",2,5)
	
	take_screenshot("3_conso",tempDir)
	
	# Téléchargement du fichier
	logger.info('Téléchargement du fichier')
	downloadFileButton = browser.find_element(By.XPATH, "//*[contains(@class, 'slds-text-title_caps') and contains(@class, 'slds-button')]")
	downloadFileButton.click()

	logger.info('Fichier: ' + downloadFile)
	time.sleep(30)

	# Resultat
	returnStatus = 1

except Exception as e: 
	if (str(e.__class__).find('TimeoutException') != -1) : 
		logger.error('La page met trop de temps a s\'afficher')
		
	else : logger.error(str(e))

	take_screenshot("Exception",tempDir) 
	
finally:
	# fermeture browser
	logger.debug('Fermeture connexion')
	if (browser is not None) : browser.quit()
		
	# Suppression fichier temporaire sauf en debug
	if (chromedriverLog is not None and os.path.exists(chromedriverLog)) : 
		if (logLevel != logging.DEBUG) : os.remove(chromedriverLog)
			
	# fermeture de l'affichage virtuel
	logger.info('Fermeture display. Exit code ' + str(returnStatus))
	if (display is not None) : display.stop()
	
	# print (returnStatus)
	sys.exit(returnStatus)

