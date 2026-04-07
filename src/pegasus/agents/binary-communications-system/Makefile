all: agent_bridge.so

agent_bridge.so: agent_bridge.c binary_bridge.c crypto_military_integration.c ring_buffer_adapter.c
	gcc -shared -fPIC -mavx2 -mpclmul -msse4.2 -o agent_bridge.so agent_bridge.c binary_bridge.c crypto_military_integration.c ring_buffer_adapter.c -luring

clean:
	rm -f agent_bridge.so
