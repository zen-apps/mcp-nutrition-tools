# CONTAINER ID   IMAGE                                                          COMMAND                  CREATED        STATUS                    PORTS                              NAMES
#d3a02eab06f7   usda-nutrition-ai-toolkit_mcp-server                           "python -m uvicorn s…"   4 hours ago    Up 4 hours (healthy)      8000/tcp, 0.0.0.0:8080->8080/tcp   usda-mcp-dev

IMAGE_NAME = usda-nutrition-ai-toolkit_mcp-server

stop:
	@containers=$$(docker ps -q --filter ancestor=$(IMAGE_NAME)); \
	if [ -n "$$containers" ]; then \
		docker stop $$containers; \
	fi

rm:
	@containers=$$(docker ps -aq --filter ancestor=$(IMAGE_NAME)); \
	if [ -n "$$containers" ]; then \
		docker rm $$containers; \
	fi

up: stop rm
	docker-compose up -d

down:
	docker-compose down
