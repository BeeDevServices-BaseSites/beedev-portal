--
-- Table structure for table `proposalApp_basesetting`
--
INSERT INTO `proposalApp_basesetting` VALUES (1,'vite-base','Vite App',300.00,'',1,0),(2,'python-default','Python Default Base',400.00,'',1,0),(3,'python-custom','Python Custom Base',500.00,'',1,0),(5,'hosting-monthly','Hosting-Monthly',20.00,'',1,0),(6,'hosting-yearly','Hosting Yearly',200.00,'',1,0),(7,'gen','General',0.00,'',1,0);

--
-- Table structure for table `proposalApp_jobrate`
--
INSERT INTO `proposalApp_jobrate` VALUES (1,'dev','Developer',35.00,1,0),(2,'design','Designer',30.00,1,0),(3,'devops','DevOps',25.00,1,0),(4,'back','Backend Developer',40.00,1,0);

--
-- Table structure for table `proposalApp_costtier`
--
INSERT INTO `proposalApp_costtier` VALUES (1,'tier01','Tier 1',0.00,1100.00,'',0,1),(2,'tier02','Tier 2',1100.01,1700.00,'',0,1),(3,'tier03','Tier 3',1700.01,NULL,'',0,1);

--
-- Table structure for table `proposalApp_catalogitem`
--
INSERT INTO `proposalApp_catalogitem` VALUES (1,'viteHome','Vite App + Home page','Vite App with Home Page',2.00,1.00,1,'',1,1,1),(2,'python-default','Python App + 3 Pages + Default Admin','',6.00,1.00,1,'',2,2,1),(3,'python-custom','Python App + 3 Pages + Custom Admin','',12.00,1.00,1,'',3,3,1),(4,'design','Site Design','',1.00,1.00,1,'',4,7,2),(5,'seo','SEO','',0.50,1.00,1,'',5,7,3),(6,'mobile','Mobile Responsivness','',0.50,1.00,1,'',6,7,1),(7,'deploy','Deployment','',1.00,1.00,1,'',7,7,3),(8,'contact-node','Contact Page w/Node Mailer','',4.00,1.00,1,'',8,7,1),(9,'privacy-terms','Privacy Policy / Terms and Conditions','',2.00,1.00,1,'',9,7,1),(10,'pages','Additional Pages','',0.50,2.00,1,'',11,7,1),(11,'blog-open','Blog - Open Source','',4.00,1.00,1,'',12,7,1),(12,'blog-custom','Blog - Custom','',8.00,1.00,1,'',14,7,1),(13,'ecomm-open','Ecommerce - Open Source','',4.00,1.00,1,'',13,7,1),(14,'ecomm-custom','Ecommerce - Custom','',16.00,1.00,1,'',15,7,1),(15,'transfer-domain','Domain Transfer','',1.00,1.00,1,'',16,7,3),(16,'hosting-monthly','Hosting-Monthly','',12.00,1.00,1,'',17,5,3),(17,'hosting-yearly','Hosting Yearly','',1.00,1.00,1,'',18,6,3),(18,'single-app-non','Single Platform App - Non Ecommerce','',16.00,1.00,1,'',19,7,1),(19,'cross-app-non','Cross Platform App - Non Ecommerce','',24.00,2.00,1,'',20,7,1),(20,'single-app-ecom','Single Platform App - Complex','',24.00,2.00,1,'',21,7,4),(21,'cross-app-ecomm','Cross Platform App - Complex','',36.00,3.00,1,'',22,7,4),(22,'back-heavy-custom','Heavy Custom Backend','',16.00,1.00,1,'',23,7,4),(23,'unsub','Unsubscribe Page','',3.00,1.00,1,'',10,7,1);

--
-- Table structure for table `proposalApp_discount`
--
INSERT INTO `proposalApp_discount` VALUES (1,'Veteran','vet','PERCENT',10.00,1,1,0),(2,'IowaCohort','iowa','PERCENT',20.00,1,1,0);