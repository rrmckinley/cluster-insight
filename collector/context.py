#!/usr/bin/python
#
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


"""Computes a context graph from raw context metadata.

The raw context metadata is gathered from a Kubernetes master and the Docker
daemons of its nodes.

Usage:

import context
context.compute_graph(format)
"""

import copy
import datetime
import re
import types

# local imports
import collector_error
import docker
import global_state
import kubernetes
import utilities


class ContextGraph(object):
  """Maintains the context graph and outputs it."""

  def __init__(self):
    self._graph_metadata = None
    self._graph_title = None
    # Set the color lookup table of various resources.
    self._graph_color = {
        'Cluster': 'black',
        'Node': 'red',
        'Service': 'darkgreen',
        'ReplicationController': 'purple',
        'Pod': 'blue',
        'Container': 'green',
        'Process': 'gold',
        'Image': 'maroon'
    }
    self._context_resources = []
    self._context_relations = []
    self._version = None
    self._id_set = set()

  def add_resource(self, rid, annotations, rtype, timestamp, obj=None):
    """Adds a resource to the context graph."""
    assert utilities.valid_string(rid)
    assert utilities.valid_string(utilities.get_attribute(
        annotations, ['label']))
    assert utilities.valid_string(rtype)
    assert utilities.valid_string(timestamp)

    # It is possible that the same resource is referenced by more than one
    # parent. In this case the resource is added only once.
    if rid in self._id_set:
      return

    # Add the resource to the context graph data structure.
    resource = {
        'id': rid,
        'type': rtype,
        'timestamp': timestamp,
        'annotations': copy.deepcopy(annotations)
    }

    if self._version is not None:
      resource['annotations']['createdBy'] = self._version

    # Do not add a 'metadata' attribute if its value is None.
    if obj is not None:
      resource['properties'] = obj

    self._context_resources.append(resource)
    self._id_set.add(rid)

  def add_relation(self, source, target, kind, label=None, metadata=None):
    """Adds a relation to the context graph."""
    assert utilities.valid_string(source) and utilities.valid_string(target)
    assert utilities.valid_string(kind)
    assert utilities.valid_optional_string(label)
    assert (metadata is None) or isinstance(metadata, types.DictType)

    # Add the relation to the context graph data structure.
    relation = {
        'source': source,
        'target': target,
        'type': kind,
    }

    # Add annotations as needed.
    relation['annotations'] = {}
    if metadata is not None:
      relation['annotations']['metadata'] = metadata

    relation['annotations']['label'] = label if label is not None else kind
    if self._version is not None:
      relation['annotations']['createdBy'] = self._version

    self._context_relations.append(relation)

  def set_version(self, version):
    assert utilities.valid_string(version)
    self._version = version

  def set_title(self, title):
    """Sets the title of the context graph."""
    self._graph_title = title

  def set_metadata(self, metadata):
    """Sets the metadata of the context graph."""
    self._graph_metadata = metadata

  def to_context_graph(self):
    """Returns the context graph in cluster-insight context graph format."""
    # return graph in Cluster-Insight context graph format.
    context_graph = {
        'success': True,
        'timestamp': datetime.datetime.now().isoformat(),
        'resources': self._context_resources,
        'relations': self._context_relations
    }
    return context_graph

  def to_context_resources(self):
    """Returns just the resources in Cluster-Insight context graph format."""
    resources = {
        'success': True,
        'timestamp': datetime.datetime.now().isoformat(),
        'resources': self._context_resources,
    }
    return resources

  def best_label(self, obj):
    """Returns the best human-readable label of the given object.

    We perfer the "alternateLabel" over "label" and a string not composed
    of only hexadecimal digits over hexadecimal digits.

    Args:
      obj: a dictionary containing an "annotations" attribute. The value
        of this attribute should be a dictionary, which may contain
        "alternateLabel" and "Label" attributes.

    Returns:
    The best human-readable label.
    """
    alt_label = utilities.get_attribute(obj, ['annotations', 'alternateLabel'])
    label = utilities.get_attribute(obj, ['annotations', 'label'])
    if (utilities.valid_string(alt_label) and
        re.search('[^0-9a-fA-F]', alt_label)):
      return alt_label
    elif utilities.valid_string(label) and re.search('[^0-9a-fA-F]', label):
      return label
    elif utilities.valid_string(alt_label):
      return alt_label
    elif utilities.valid_string(label):
      return label
    else:
      # should not arrive here.
      return '<unknown>'

  def to_dot_graph(self, show_node_labels=True):
    """Returns the context graph in DOT graph format."""
    if show_node_labels:
      resource_list = [
          '"{0}"[label="{1}",color={2}]'.format(
              res['id'],
              res['type'] + ':' + self.best_label(res),
              self._graph_color.get(res['type']) or 'black')
          for res in self._context_resources]
    else:
      resource_list = [
          '"{0}"[label="",fillcolor={1},style=filled]'.format(
              res['id'],
              self._graph_color.get(res['type']) or 'black')
          for res in self._context_resources]
    relation_list = [
        '"{0}"->"{1}"[label="{2}"]'.format(
            rel['source'], rel['target'], self.best_label(rel))
        for rel in self._context_relations]
    graph_items = resource_list + relation_list
    graph_data = 'digraph{' + ';'.join(graph_items) + '}'
    return graph_data

  def dump(self, gs, output_format):
    """Returns the context graph in the specified format."""
    assert isinstance(gs, global_state.GlobalState)
    assert isinstance(output_format, types.StringTypes)

    if output_format == 'dot':
      return self.to_dot_graph()
    elif output_format == 'context_graph':
      return self.to_context_graph()
    elif output_format == 'resources':
      return self.to_context_resources()
    else:
      msg = 'invalid dump() output_format: %s' % output_format
      gs.logger_error(msg)
      raise collector_error.CollectorError(msg)


def _make_error(error_message):
  """Returns an error response in the Cluster-Insight context graph format.

  Args:
    error_message: the error message describing the failure.

  Returns:
    An error response in the cluster-insight context graph format.
  """
  assert isinstance(error_message, types.StringTypes) and error_message
  return {'_success': False,
          '_timestamp': datetime.datetime.now().isoformat(),
          '_error_message': error_message}


@utilities.global_state_string_args
def _do_compute_graph(gs, output_format):
  """Returns the context graph in the specified format.

  Args:
    gs: the global state.
    output_format: one of 'graph', 'dot', 'context_graph', or 'resources'.

  Returns:
    A successful response in the specified format.

  Raises:
    CollectorError: inconsistent or invalid graph data.
  """
  g = ContextGraph()
  g.set_version(docker.get_version(gs))
  g.set_metadata({'timestamp': datetime.datetime.now().isoformat()})

  # Nodes
  nodes_list = kubernetes.get_nodes(gs)
  if not nodes_list:
    return g.dump(gs, output_format)

  # Get the project name from the first node.
  project_id = utilities.node_id_to_project_name(nodes_list[0]['id'])

  # TODO(vasbala): how do we get the name of this Kubernetes cluster?
  cluster_id = project_id
  cluster_guid = 'Cluster:' + cluster_id
  g.set_title(cluster_id)
  g.add_resource(cluster_guid, {'label': cluster_id}, 'Cluster',
                 nodes_list[0]['timestamp'])

  for node in nodes_list:
    node_id = node['id']
    node_guid = 'Node:' + node_id
    g.add_resource(node_guid, node['annotations'], 'Node', node['timestamp'],
                   node['properties'])
    g.add_relation(cluster_guid, node_guid, 'contains')  # Cluster contains Node
    # Pods in a Node
    for pod in kubernetes.get_pods(gs, node_id):
      pod_id = pod['id']
      pod_guid = 'Pod:' + pod_id
      docker_host = utilities.get_attribute(
          pod, ['properties', 'currentState', 'host'])
      if not utilities.valid_string(docker_host):
        msg = ('Docker host (pod["properties"]["currentState"]["host"]) '
               'not found in pod ID %s' % pod_id)
        gs.logger_error(msg)
        raise collector_error.CollectorError(msg)

      g.add_resource(pod_guid, pod['annotations'], 'Pod', pod['timestamp'],
                     pod['properties'])
      g.add_relation(node_guid, pod_guid, 'runs')  # Node runs Pod
      # Containers in a Pod
      for container in docker.get_containers(gs, docker_host, pod_id):
        container_id = container['id']
        container_guid = 'Container:' + container_id
        # TODO(vasbala): container_id is too verbose?
        g.add_resource(container_guid, container['annotations'],
                       'Container', container['timestamp'],
                       container['properties'])
        # Pod contains Container
        g.add_relation(pod_guid, container_guid, 'contains')
        # Processes in a Container
        for process in docker.get_processes(gs, docker_host, container_id):
          process_id = process['id']
          process_guid = 'Process:' + process_id
          g.add_resource(process_guid, process['annotations'],
                         'Process', process['timestamp'], process['properties'])
          # Container contains Process
          g.add_relation(container_guid, process_guid, 'contains')
        # Image from which this Container was created
        image_id = utilities.get_attribute(
            container, ['properties', 'Config', 'Image'])
        if not utilities.valid_string(image_id):
          # Image ID not found
          continue
        image = docker.get_image(gs, docker_host, image_id)
        if image is None:
          # image not found
          continue
        image_guid = 'Image:' + image['id']
        g.add_resource(image_guid, image['annotations'], 'Image',
                       image['timestamp'], image['properties'])
        # Container createdFrom Image
        g.add_relation(container_guid, image_guid, 'createdFrom')

  # Services
  for service in kubernetes.get_services(gs):
    service_id = service['id']
    service_guid = 'Service:' + service_id
    g.add_resource(service_guid, service['annotations'], 'Service',
                   service['timestamp'], service['properties'])
    # Cluster contains Service.
    g.add_relation(cluster_guid, service_guid, 'contains')
    # Pods load balanced by this Service (use the service['labels']
    # key/value pairs to find matching Pods)
    selector = service['properties'].get('labels')
    if selector:
      for pod in kubernetes.get_selected_pods(gs, selector):
        pod_guid = 'Pod:' + pod['id']
        # Service loadBalances Pod
        g.add_relation(service_guid, pod_guid, 'loadBalances')
    else:
      gs.logger_error('Service id=%s has no "labels" key', service_id)

  # ReplicationControllers
  rcontrollers_list = kubernetes.get_rcontrollers(gs)
  for rcontroller in rcontrollers_list:
    rcontroller_id = rcontroller['id']
    rcontroller_guid = 'ReplicationController:' + rcontroller_id
    g.add_resource(rcontroller_guid, rcontroller['annotations'],
                   'ReplicationController',
                   rcontroller['timestamp'], rcontroller['properties'])
    # Cluster contains Rcontroller
    g.add_relation(cluster_guid, rcontroller_guid, 'contains')
    # Pods that are monitored by this Rcontroller (use the rcontroller['labels']
    # key/value pairs to find matching pods)
    selector = rcontroller['properties'].get('labels')
    if selector:
      for pod in kubernetes.get_selected_pods(gs, selector):
        pod_guid = 'Pod:' + pod['id']
        # Rcontroller monitors Pod
        g.add_relation(rcontroller_guid, pod_guid, 'monitors')
    else:
      gs.logger_error('Rcontroller id=%s has no "labels" key', rcontroller_id)

  # Dump the resulting graph
  return g.dump(gs, output_format)


@utilities.global_state_string_args
def compute_graph(gs, output_format):
  """Collects raw information and computes the context graph.

  Args:
    gs: global state.
    output_format: one of 'graph', 'dot', 'context_graph', or 'resources'.

  Returns:
  The context graph in the specified format.
  """
  return _do_compute_graph(gs, output_format)
