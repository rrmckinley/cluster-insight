# Copyright 2015 The Cluster-Insight Authors. All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Makefile for testing the Cluster-Insight data collector.
#
# Do not use this Makefile for building the Cluster-Insight data collector.
# Please read Dockerfile for details on building this service.
PYTHON="python"

test: test_utilities test_cache test_collector test_docker_proxy test_global_state

test_cache: simple_cache_test.py
	$(PYTHON) $^

test_utilities: utilities_test.py
	$(PYTHON) $^

test_collector: collector_test.py
	$(PYTHON) $^

test_docker_proxy: docker_proxy_test.py
	$(PYTHON) $^

test_global_state: global_state_test.py
	$(PYTHON) $^
