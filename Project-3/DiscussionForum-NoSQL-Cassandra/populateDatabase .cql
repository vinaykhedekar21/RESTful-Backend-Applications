INSERT INTO discussionforum.user (user_id, username, password) VALUES(ef2a83c6-3f9a-11e8-ad30-08002705014c, 'vinay', 'Vinay@21');

INSERT INTO discussionforum.user (user_id, username, password) VALUES(f2722e30-3f9a-11e8-ad30-08002705014c, 'samarth', 'Samarth@21');

INSERT INTO discussionforum.user (user_id, username, password) VALUES(f5c4c304-3f9a-11e8-ad30-08002705014c, 'rani','Rani@21');

INSERT INTO discussionforum.forum (forum_id, name, creator) VALUES(06a2ed68-3f9b-11e8-ad30-08002705014c, 'Redis','vinay');

INSERT INTO discussionforum.forum (forum_id, name, creator) VALUES(08456844-3f9b-11e8-ad30-08002705014c, 'MongoDB','samarth');

INSERT INTO discussionforum.forum (forum_id, name, creator) VALUES(09c9ea14-3f9b-11e8-ad30-08002705014c, 'AWS','rani');

INSERT INTO discussionforum.thread_post JSON '{"thread_id":"15596bac-3f9b-11e8-ad30-08002705014c", "forum_id":"06a2ed68-3f9b-11e8-ad30-08002705014c", 
						"title":"Does anyone know how to start MongoDB?", "creator":"vinay", "timestamp": "2011-02-03 04:05+0000",
						"posts":['{author: 'vinay', text: 'I guess sudo start MongoDB?', timestamp: '2011-03-03 04:05+0000'},
								  {author: 'samarth', text: 'flask run MongoDB?', timestamp: '2011-02-03 05:05+0000'}']}';

INSERT INTO discussionforum.thread_post JSON '{"thread_id":"538b51b0-f922-11e8-8eb2-f2801f1b9fd1", "forum_id":"61694ddc-f922-11e8-8eb2-f2801f1b9fd1", 
						"title":"Does anyone know how to start Redis?", "creator":"vinay", "timestamp": "2011-02-03 04:05+0000",
						"posts":['{author: 'vinay', text: 'flask run Redis?', timestamp: '2011-04-03 04:05+0000'},
								  {author: 'samarth', text: 'sudo start Redis?', timestamp: '2011-04-04 04:05+0000'}, 
								  {author: 'rani', text: 'start Redis?', timestamp: '2011-04-04 05:05+0000'}']}';