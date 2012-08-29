# Software License Agreement (BSD License)
#
# Copyright (c) 2012, Fraunhofer FKIE/US, Alexander Tiderko
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of I Heart Engineering nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from urlparse import urlparse

from PySide import QtCore
from PySide import QtGui

import roslib
import rospy
import node_manager_fkie as nm
from master_discovery_fkie.master_info import NodeInfo 


################################################################################
##############                  GrouptItem                        ##############
################################################################################

class GroupItem(QtGui.QStandardItem):
  '''
  The GroupItem stores the information about a group of nodes. 
  '''
  ITEM_TYPE = QtCore.Qt.UserRole + 25
  
  def __init__(self, name, parent=None):
    '''
    Initialize the GroupItem object with given values.
    @param name: the name of the group
    @type name: C{str}
    @param parent: the parent item. In most cases this is the HostItem. The 
    variable is used to determine the different columns of the NodeItem. 
    @type parent: L{PySide.QtGui.QStandardItem}
    '''
    QtGui.QStandardItem.__init__(self, GroupItem.toHTML(name))
    self.parent_item = parent
    self._name = name
    self.setIcon(QtGui.QIcon(':/icons/state_off.png'))
    self.descr_type = self.descr_name = self.descr = ''
    self.descr_images = []
    self._capcabilities = dict()
    ''' 
     @ivar: dict(config : dict(namespace: dict(group:dict('type' : str, 'images' : [str], 'description' : str, 'nodes' : [str]))))
    '''
  
  @property
  def name(self):
    '''
    The name of this group.
    @rtype: C{str}
    '''
    return self._name
  
  @name.setter
  def name(self, new_name):
    '''
    Set the new name of this group and updates the displayed name of the item.
    @param new_name: The new name of the group. Used also to identify the group.
    @type new_name: C{str}
    '''
    self._name = new_name
    self.setText(GroupItem.toHTML(self._name))
  
  def addCapabilities(self, config, capabilities, masteruri):
    '''
    Add new capabilities. Based on this capabilities the node are grouped. The 
    view will be updated.
    @param config: The name of the configuration containing this new capabilities.
    @type config: C{str}
    @param masteruri: The masteruri is used only used, if new nodes are created.
    @type masteruri: C{str}
    @param capabilities: The capabilities, which defines groups and containing nodes.
    @type capabilities: C{dict(namespace: dict(group:dict('type' : str, 'images' : [str], 'description' : str, 'nodes' : [str])))}
    '''
    self._capcabilities[config] = capabilities 
    # update the view
    for ns, groups in capabilities.items():
      for group, descr in groups.items():
        # create nodes for each group
        nodes = descr['nodes']
        if nodes:
          groupItem = self.getGroupItem(roslib.names.ns_join(ns, group))
          groupItem.descr_name = group
          if descr['type']:
            groupItem.descr_type = descr['type']
          if descr['description']:
            groupItem.descr = descr['description']
          if descr['images']:
            groupItem.descr_images = list(descr['images'])
          # move the nodes from host to the group
          for i in reversed(range(self.rowCount())):
            item = self.child(i)
            if isinstance(item, NodeItem) and item.name in nodes:
              row = self.takeRow(i)
              groupItem._addRow_sorted(row)
#              row[0].parent_item = groupItem
              groupItem.updateDisplayedConfig()

          # create new or update existing items in the group
          for node_name in nodes:
            items = groupItem.getNodeItemsByName(node_name)
            if items:
              for item in items:
                item.addConfig(config)
            else:
              items = self.getNodeItemsByName(node_name)
              if items:
                # copy the state of the existing node
                groupItem.addNode(items[0].node_info, config)
              else:
                groupItem.addNode(NodeInfo(node_name, masteruri), config)
          groupItem.updateIcon()
          groupItem.updateTooltip()

  def remCapablities(self, config):
    '''
    Removes internal entry of the capability, so the new nodes are not grouped.
    To update view L{NodeTreeModel.removeConfigNodes()} and L{GroupItem.clearUp()}
    must be called.
    @param config: The name of the configuration containing this new capabilities.
    @type config: C{str}
    '''
    try:
      if self._capcabilities.has_key(config):
        del self._capcabilities[config]
    except:
      pass
    else:
      #todo update view?
      pass

  def getCapabilityGroups(self, node_name, cfg=''):
    '''
    Returns the names of groups, which contains the given node.
    @param node_name: The name of the node
    @type node_name: C{str}
    @param cfg: The name of configuration, which describes the node.
    @type cfg: C{str}
    @return: The name of the configuration containing this new capabilities.
    @rtype: C{dict(config : [str])}
    '''
    result = dict() # dict(config : [group names])
    try:
      if cfg:
        for ns, groups in self._capcabilities[cfg].items():
          for group, descr in groups.items():
            if node_name in descr['nodes']:
              if not result.has_key(c):
                result[c] = []
              result[c].append(roslib.ns_join(ns, group))
    except:
      pass
#      import traceback
#      print traceback.format_exc()
    return result

  def getNodeItemsByName(self, node_name, recursive=True):
    '''
    Since the same node can be included by different groups, this method searches
    for all nodes with given name and returns these items. 
    @param node_name: The name of the node
    @type node_name: C{str}
    @param recursive: Searches in (sub) groups
    @type recursive: C{bool}
    @return: The list with node items.
    @rtype: C{[L{PySide.QtGui.QStandardItem}]}
    '''
    result = []
    for i in range(self.rowCount()):
      item = self.child(i)
      if isinstance(item, GroupItem):
        if recursive:
          result[len(result):] = item.getNodeItemsByName(node_name)
      elif isinstance(item, NodeItem) and item == node_name:
        return [item]
    return result

  def getNodeItems(self):
    '''
    Returns all nodes in this group and subgroups.
    @return: The list with node items.
    @rtype: C{[L{PySide.QtGui.QStandardItem}]}
    '''
    result = []
    for i in range(self.rowCount()):
      item = self.child(i)
      if isinstance(item, GroupItem):
        result[len(result):] = item.getNodeItems()
      elif isinstance(item, NodeItem):
        result.append(item)
    return result

  def getGroupItems(self):
    '''
    Returns all group items this group
    @return: The list with group items.
    @rtype: C{[L{GroupItem}]}
    '''
    result = []
    for i in range(self.rowCount()):
      item = self.child(i)
      if isinstance(item, GroupItem):
        result.append(item)
        result[len(result):] = item.getGroupItems()
    return result


  def getGroupItem(self, group_name):
    '''
    Returns a GroupItem with given name. If no group with this name exists, a 
    new one will be created.
    Assumption: No groups in group!!
    @param group_name: the name of the group
    @type group_name: C{str} 
    @return: The group with given name
    @rtype: L{GroupItem} 
    '''
    for i in range(self.rowCount()):
      item = self.child(i)
      if isinstance(item, GroupItem):
        if item == group_name:
          return item
        elif item > group_name:
          items = []
          newItem = GroupItem(group_name, self)
          items.append(newItem)
          cfgitem = QtGui.QStandardItem()
          items.append(cfgitem)
          self.insertRow(i, items)
          return newItem
    items = []
    newItem = GroupItem(group_name, self)
    items.append(newItem)
    cfgitem = QtGui.QStandardItem()
    items.append(cfgitem)
    self.appendRow(items)
    return newItem

  def addNode(self, node, cfg=''):
    '''
    Adds a new node with given name.
    @param node: the NodeInfo of the node to create
    @type node: L{NodeInfo}
    @param cfg: The configuration, which describes the node
    @type cfg: C{str}
    '''
    groups = self.getCapabilityGroups(node.name, cfg)
    if groups:
      for c, group_list in groups.items():
        for group_name in group_list:
          # insert in the group
          groupItem = self.getGroupItem(group_name)
          groupItem.addNode(node)
    else:
      # insert in order
      new_item_row = NodeItem.newNodeRow(node.name, node.masteruri)
      self._addRow_sorted(new_item_row)
      new_item_row[0].node_info = node
#      new_item_row[0].parent_item = self
      if cfg:
        new_item_row[0].addConfig(cfg)

  def _addRow_sorted(self, row):
    for i in range(self.rowCount()):
      item = self.child(i)
      if item > row[0].name:
        self.insertRow(i, row)
        row[0].parent_item = self
        return
    self.appendRow(row)
    row[0].parent_item = self

  def clearUp(self, fixed_node_names = None):
    '''
    Removes not running and not configured nodes.
    @param fixed_node_names: If the list is not None, the node not in the list are
    set to not running!
    @type fixed_node_names: C{[str]}
    '''
    # first clear sub groups
    groups = self.getGroupItems()
    for group in groups:
      group.clearUp(fixed_node_names)

    # move running nodes without configuration to the upper layer, remove not running and duplicate nodes
    for i in reversed(range(self.rowCount())):
      item = self.child(i)
      if isinstance(item, NodeItem):
        # set the running state of the node to None
        if not fixed_node_names is None and not item.name in fixed_node_names:
          item.node_info = NodeInfo(item.name, item.node_info.masteruri)
        if not item.is_valid():
          self.removeRow(i)
        elif not isinstance(self, HostItem):
          if item.state == NodeItem.STATE_RUN and len(item.cfgs) == 0:
            # if it is in a group, is running, but has no configuration, move it to the host
            if not self.parent_item is None and isinstance(self.parent_item, HostItem):
              items_in_host = self.parent_item.getNodeItemsByName(item.name, False)
              if len(items_in_host) == 0:
                row = self.takeRow(i)
                self.parent_item._addRow_sorted(row)
#                row[0].parent_item = self.parent_item
              else:
                #remove item
                self.removeRow(i)

    # remove empty groups 
    for i in reversed(range(self.rowCount())):
      item = self.child(i)
      if isinstance(item, GroupItem):
        # remove empty groups
        if item.rowCount() == 0:
          self.removeRow(i)

  def updateRunningNodeState(self, nodes):
    '''
    Updates the running state of the nodes given in a dictionary.
    @param nodes: A dictionary with node names and their running state described by L{NodeInfo}.
    @type nodes: C{dict(str: L{master_discovery_fkie.NodeInfo})}
    '''
    for (name, node) in nodes.items():
      # get the node items
      items = self.getNodeItemsByName(name)
      if items:
        for item in items:
          # update the node item
          item.node_info = node
      else:
        # create the new node
        self.addNode(node)
    self.clearUp(nodes.keys())

  def getRunningNodes(self):
    '''
    Returns the names of all running nodes. A running node is defined by his 
    PID. 
    @see: L{master_dicovery_fkie.NodeInfo}
    @return: A list with node names
    @rtype: C{[str]}
    '''
    result = []
    for i in range(self.rowCount()):
      item = self.child(i)
      if isinstance(item, GroupItem):
        result[len(result):] = item.getRunningNodes()
      elif isinstance(item, NodeItem) and not item.node_info.pid is None:
        result.append(item.name)
    return result

  def markNodesAsDuplicateOf(self, running_nodes):
    '''
    While a synchronization same node on different hosts have the same name, the 
    nodes with the same on other host are marked.
    @param running_nodes: A list with node names, which are running on other hosts.
    @type running_nodes: C{[str]}
    '''
    ignore = ['/master_sync', '/master_discovery', '/node_manager']
    for i in range(self.rowCount()):
      item = self.child(i)
      if isinstance(item, GroupItem):
        item.markNodesAsDuplicateOf(running_nodes)
      elif isinstance(item, NodeItem):
        item.has_running = (item.node_info.uri is None and not item.name in ignore and item.name in running_nodes)

  def updateIcon(self):
    has_running = False
    has_off = False
    has_duplicate = False
    for i in range(self.rowCount()):
      item = self.child(i)
      if isinstance(item, NodeItem):
        if item.state == NodeItem.STATE_WARNING:
          self.setIcon(QtGui.QIcon(':/icons/crystal_clear_warning.png'))
          return
        elif item.state == NodeItem.STATE_OFF:
          has_off = True
        elif item.state == NodeItem.STATE_RUN:
          has_running = True
        elif item.state == NodeItem.STATE_DUPLICATE:
          has_duplicate = True
    if has_duplicate:
      self.setIcon(QtGui.QIcon(':/icons/imacadam_stop.png'))
    elif has_running and has_off:
      self.setIcon(QtGui.QIcon(':/icons/state_part.png'))
    elif not has_running:
      self.setIcon(QtGui.QIcon(':/icons/state_off.png'))
    elif not has_off and has_running:
      self.setIcon(QtGui.QIcon(':/icons/state_run.png'))
  
  def _create_html_list(self, title, items):
    result = ''
    if items:
      result = ''.join([result, '<b><u>', title,'</u></b>'])
      if len(items) > 1:
        result = ''.join([result, ' [', str(len(items)),']'])
      result = ''.join([result, '<ul>'])
      for i in items:
        result = ''.join([result, '<li>', i, '</li>'])
      result = ''.join([result, '</ul>'])
    return result

  def updateTooltip(self):
    '''
    Creates a tooltip description based on text set by L{updateDescription()} 
    and all childs of this host with valid sensor description. The result is
    returned as a HTML part.
    @return: the tooltip description coded as a HTML part 
    @rtype: C{str}
    '''
    tooltip = self.generateDescription(False)
    self.setToolTip(tooltip if tooltip else self.name)
    return tooltip
  
  def generateDescription(self, extended=True):
    tooltip = ''
    if self.descr_type or self.descr_name or self.descr:
      tooltip = ''.join(['<h4>', self.descr_name, '</h4><dl>'])
      if self.descr_type:
        tooltip = ''.join([tooltip, '<dt>Type: ', self.descr_type, '</dt></dl>'])
      if extended:
        try:
          from docutils import examples
          if self.descr:
            tooltip = ''.join([tooltip, '<b><u>Detailed description:</u></b>'])
            tooltip = ''.join([tooltip, examples.html_body(self.descr)])
        except:
          import traceback
          rospy.logwarn("Error while generate description for a tooltip: %s", str(traceback.format_exc()))
          tooltip = ''.join([tooltip, '<br>'])
      # get nodes
      nodes = []
      for j in range(self.rowCount()):
        nodes.append(self.child(j).name)
      if nodes:
        tooltip = ''.join([tooltip, self._create_html_list('Nodes:', nodes)])
    return ''.join(['<div>', tooltip, '</div>']) if tooltip else ''

  def updateDescription(self, descr_type, descr_name, descr):
    '''
    Sets the description of the robot. To update the tooltip of the host item use L{updateTooltip()}.
    @param descr_type: the type of the robot
    @type descr_type: C{str}
    @param descr_name: the name of the robot
    @type descr_name: C{str}
    @param descr: the description of the robot as a U{http://docutils.sourceforge.net/rst.html|reStructuredText} 
    @type descr: C{str}
    '''
    self.descr_type = descr_type
    self.descr_name = descr_name
    self.descr = descr

  def updateDisplayedConfig(self):
    '''
    Updates the configuration representation in other column.
    '''
    if not self.parent_item is None:
      # get nodes
      cfgs = []
      for j in range(self.rowCount()):
        cfgs[len(cfgs):] = self.child(j).cfgs
      if cfgs:
        cfgs = list(set(cfgs))
      cfg_col = self.parent_item.child(self.row(), NodeItem.COL_CFG)
      if not cfg_col is None and isinstance(cfg_col, QtGui.QStandardItem):
        cfg_col.setText(str(''.join(['[',str(len(cfgs)),']'])) if len(cfgs) > 1 else "")
        # set tooltip
        tooltip = ''
        if len(cfgs) > 0:
          tooltip = ''
          if len(cfgs) > 0:
            tooltip = ''.join([tooltip, '<h4>', 'Configurations:', '</h4><dl>'])
            for c in cfgs:
              if NodeItem.is_default_cfg(c):
                tooltip = ''.join([tooltip, '<dt>[default]', c[0], '</dt>'])
              else:
                tooltip = ''.join([tooltip, '<dt>', c, '</dt>'])
            tooltip = ''.join([tooltip, '</dl>'])
        cfg_col.setToolTip(''.join(['<div>', tooltip, '</div>']))
        # set icons
        has_launches = NodeItem.has_launch_cfgs(cfgs)
        has_defaults = NodeItem.has_default_cfgs(cfgs)
        if has_launches and has_defaults:
          cfg_col.setIcon(QtGui.QIcon(':/icons/crystal_clear_launch_file_def_cfg.png'))
        elif has_launches:
          cfg_col.setIcon(QtGui.QIcon(':/icons/crystal_clear_launch_file.png'))
        elif has_defaults:
          cfg_col.setIcon(QtGui.QIcon(':/icons/default_cfg.png'))
        else:
          cfg_col.setIcon(QtGui.QIcon())
  
  @classmethod
  def toHTML(cls, group_name):
    '''
    Creates a HTML representation of the group name.
    @param group_name: the name of the group
    @type group_name: C{str}
    @return: the HTML representation of the name of the group
    @rtype: C{str}
    '''
    ns, sep, name = group_name.rpartition('/')
    result = ''
    if sep:
      result = ''.join(['<div>', '<span style="color:gray;">', ns, sep, '</span><b>[', name, ']</b></div>'])
    else:
      result = name
    return result

  def type(self):
    return GroupItem.ITEM_TYPE

  def __eq__(self, item):
    '''
    Compares the name of the group.
    '''
    if isinstance(item, str) or isinstance(item, unicode):
      return self.name.lower() == item.lower()
    elif not (item is None):
      return self.name.lower() == item.name.lower()
    return False

  def __gt__(self, item):
    '''
    Compares the name of the group.
    '''
    if isinstance(item, str) or isinstance(item, unicode):
      return self.name.lower() > item.lower()
    elif not (item is None):
      return self.name.lower() > item.name.lower()
    return False



################################################################################
##############                   HostItem                         ##############
################################################################################

class HostItem(GroupItem):
  '''
  The HostItem stores the information about a host. 
  '''
  ITEM_TYPE = QtCore.Qt.UserRole + 26
  
  def __init__(self, address, local, parent=None):
    '''
    Initialize the HostItem object with given values.
    @param address: the address of the host
    @type address: C{str}
    @param local: is this host the localhost where the node_manager is running.
    @type local: C{bool}
    '''
    name = nm.nameres().getName(host=address)
    if not name:
      name = address
    GroupItem.__init__(self, NodeItem.toHTML(name), parent)
    self.address = address
    if QtCore.QFile.exists(''.join([nm.ROBOTS_DIR, name, '.png'])):
      self.setIcon(QtGui.QIcon(''.join([nm.ROBOTS_DIR, name, '.png'])))
    else:
      if local:
        self.setIcon(QtGui.QIcon(':/icons/crystal_clear_miscellaneous.png'))
      else:
        self.setIcon(QtGui.QIcon(':/icons/remote.png'))
    self.descr_type = self.descr_name = self.descr = ''
  
  def updateTooltip(self):
    '''
    Creates a tooltip description based on text set by L{updateDescription()} 
    and all childs of this host with valid sensor description. The result is
    returned as a HTML part.
    @return: the tooltip description coded as a HTML part 
    @rtype: C{str}
    '''
    tooltip = self.generateDescription(False)
    self.setToolTip(tooltip if tooltip else self.name)
    return tooltip
  
  def generateDescription(self, extended=True):
    tooltip = ''
    if self.descr_type or self.descr_name or self.descr:
      tooltip = ''.join(['<h4>', self.descr_name, '</h4><dl>'])
      if self.descr_type:
        tooltip = ''.join([tooltip, '<dt>Type: ', self.descr_type, '</dt></dl>'])
      if extended:
        try:
          from docutils import examples
          if self.descr:
            tooltip = ''.join([tooltip, '<b><u>Detailed description:</u></b>'])
            tooltip = ''.join([tooltip, examples.html_body(self.descr, input_encoding='utf8')])
        except:
          import traceback
          rospy.logwarn("Error while generate description for a tooltip: %s", str(traceback.format_exc()))
          tooltip = ''.join([tooltip, '<br>'])
    # get sensors
    capabilities = []
    for j in range(self.rowCount()):
      item = self.child(j)
      if isinstance(item, GroupItem):
        capabilities.append(item.name)
    if capabilities:
      tooltip = ''.join([tooltip, '<b><u>Capabilities:</u></b>'])
      try:
        from docutils import examples
        tooltip = ''.join([tooltip, examples.html_body(''.join(['- ', '\n- '.join(capabilities)]), input_encoding='utf8')])
      except:
        import traceback
        rospy.logwarn("Error while generate description for a tooltip: %s", str(traceback.format_exc()))
    return ''.join(['<div>', tooltip, '</div>']) if tooltip else ''
  
  def type(self):
    return HostItem.ITEM_TYPE

  def __eq__(self, item):
    '''
    Compares the address of the host.
    '''
    if isinstance(item, str) or isinstance(item, unicode):
      return self.address.lower() == item.lower()
    elif not (item is None):
      return self.address.lower() == item.name.lower()
    return False

  def __gt__(self, item):
    '''
    Compares the address of the host.
    '''
    if isinstance(item, str) or isinstance(item, unicode):
      return self.address.lower() > item.lower()
    elif not (item is None):
      return self.address.lower() > item.name.lower()
    return False


################################################################################
##############                   NodeItem                         ##############
################################################################################

class NodeItem(QtGui.QStandardItem):
  '''
  The NodeItem stores the information about the node using the ExtendedNodeInfo
  class and represents it in a L{PySide.QtGui.QTreeModel} using the 
  L{PySide.QtGui.QStandardItemModel}
  '''
  
  ITEM_TYPE = QtGui.QStandardItem.UserType + 35
  COL_CFG = 1
#  COL_URI = 2

  STATE_OFF = 0
  STATE_RUN = 1
  STATE_WARNING = 2
  STATE_DUPLICATE = 3

  def __init__(self, node_info):
    '''
    Initialize the NodeItem instance.
    @param node_info: the node information
    @type node_info: L{master_discovery_fkie.NodeInfo}
    '''
    QtGui.QStandardItem.__init__(self, self.toHTML(node_info.name))
    self.parent_item = None
    self._node_info = node_info.copy()
#    self.ICONS = {'empty' : QtGui.QIcon(),
#                  'run'    : QtGui.QIcon(':/icons/state_run.png'),
#                  'off'     :QtGui.QIcon(':/icons/state_off.png'),
#                  'warning' : QtGui.QIcon(':/icons/crystal_clear_warning.png'),
#                  'stop'    : QtGui.QIcon('icons/imacadam_stop.png'),
#                  'cfg+def' : QtGui.QIcon(':/icons/crystal_clear_launch_file_def_cfg.png'),
#                  'cfg'     : QtGui.QIcon(':/icons/crystal_clear_launch_file.png'),
#                  'default_cfg' : QtGui.QIcon(':/icons/default_cfg.png')
#                  }
    self._cfgs = []
    self._has_running = False
    self.setIcon(QtGui.QIcon(':/icons/state_off.png'))
    self._state = NodeItem.STATE_OFF

  @property
  def state(self):
    return self._state
  
  def is_valid(self):
    '''
    Returns C{True} if the node has no configuration and is not running, so the pid 
    and node URI are C{None}
    @rtype: C{bool}
    '''
    return not (self._node_info.pid is None and self._node_info.uri is None and len(self._cfgs) == 0)

  @property
  def name(self):
    return self._node_info.name

  @property
  def masteruri(self):
    return self._node_info.masteruri

  @property
  def published(self):
    return self._node_info.publishedTopics

  @property
  def subscribed(self):
    return self._node_info.subscribedTopics

  @property
  def services(self):
    return self._node_info.services

  @property
  def node_info(self):
    '''
    Returns the NodeInfo instance of this node.
    @rtype: L{master_discovery_fkie.NodeInfo}
    '''
    return self._node_info

  @node_info.setter
  def node_info(self, node_info):
    '''
    Sets the NodeInfo and updates the view, if needed.
    '''
    abbos_changed = False
    run_changed = False
    if self._node_info.publishedTopics != node_info.publishedTopics:
      abbos_changed = True
      self._node_info._publishedTopics = list(node_info.publishedTopics)
    if self._node_info.subscribedTopics != node_info.subscribedTopics:
      abbos_changed = True
      self._node_info._subscribedTopics = list(node_info.subscribedTopics)
    if self._node_info.services != node_info.services:
      abbos_changed = True
      self._node_info._services = list(node_info.services)
    if self._node_info.pid != node_info.pid:
      self._node_info.pid = node_info.pid
      run_changed = True
    if self._node_info.uri != node_info.uri:
      self._node_info.uri = node_info.uri
      run_changed = True
    # update the tooltip and icon
    if run_changed and self.is_valid():
      self.updateDispayedName()
#      self.updateDisplayedURI()
      if not self.parent_item is None and not isinstance(self.parent_item, HostItem):
        self.parent_item.updateIcon()
  
  @property
  def uri(self):
    return self._node_info.uri

  @property
  def pid(self):
    return self._node_info.pid

  @property
  def has_running(self):
    '''
    Returns C{True}, if there are exists other nodes with the same name. This 
    variable must be set manually! 
    @rtype: C{bool}
    '''
    return self._has_running

  @has_running.setter
  def has_running(self, state):
    '''
    Sets however other node with the same name are running or not (on other hosts)
    and updates the view oth this item.
    '''
    if self._has_running != state:
      self._has_running = state
      if self.is_valid():
        self.updateDispayedName()
      if not self.parent_item is None and not isinstance(self.parent_item, HostItem):
        self.parent_item.updateIcon()


  def updateDispayedName(self):
    '''
    Updates the name representation of the Item
    '''
    tooltip = ''.join(['<h4>', self.node_info.name, '</h4><dl>'])
    tooltip = ''.join([tooltip, '<dt><b>URI:</b> ', str(self.node_info.uri), '</dt>'])
    tooltip = ''.join([tooltip, '<dt><b>PID:</b> ', str(self.node_info.pid), '</dt></dl>'])
    uri = nm.nameres().getUri(host=nm.nameres().getHostname(self.node_info.uri))
    master_discovered = (not uri is None)
    local = False
    if not self.node_info.uri is None and not self.node_info.masteruri is None:
      local = (nm.nameres().getHostname(self.node_info.uri) == nm.nameres().getHostname(self.node_info.masteruri))
    if not self.node_info.pid is None:
      self._state = NodeItem.STATE_RUN
      self.setIcon(QtGui.QIcon(':/icons/state_run.png'))
    elif not local and not master_discovered and not self.node_info.uri is None:
      self._state = NodeItem.STATE_RUN
      self.setIcon(QtGui.QIcon(':/icons/state_run.png'))
      tooltip = ''.join([tooltip, '<dl><dt>(Remote nodes will not be ping, so they are always marked running)</dt></dl>'])
    elif not self.node_info.uri is None:
      self._state = NodeItem.STATE_WARNING
      self.setIcon(QtGui.QIcon(':/icons/crystal_clear_warning.png'))
      if not local and master_discovered:
        tooltip = ''.join(['<h4>', self.node_info.name, ' is not local, however the ROS master on this host is discovered, but no information about this node received!', '</h4>'])
    elif self.has_running:
      self._state = NodeItem.STATE_DUPLICATE
      self.setIcon(QtGui.QIcon(':/icons/imacadam_stop.png'))
      tooltip = ''.join(['<h4>Where are nodes with the same name on remote hosts running. These will be terminated, if you run this node!</h4>'])
    else:
      self._state = NodeItem.STATE_OFF
      self.setIcon(QtGui.QIcon(':/icons/state_off.png'))
    tooltip = ''.join([tooltip, '</dl>'])
    self.setToolTip(''.join(['<div>', tooltip, '</div>']))

  def updateDisplayedURI(self):
    '''
    Updates the URI representation in other column.
    '''
    if not self.parent_item is None:
      uri_col = self.parent_item.child(self.row(), NodeItem.COL_URI)
      if not uri_col is None and isinstance(uri_col, QtGui.QStandardItem):
        uri_col.setText(str(self.node_info.uri) if not self.node_info.uri is None else "")

  @property
  def cfgs(self):
    '''
    Returns the list with all launch configurations assigned to this item.
    @rtype: C{[str]}
    '''
    return self._cfgs

  def addConfig(self, cfg):
    '''
    Add the given configurations to the node.
    @param cfg: the loaded configuration, which contains this node.
    @type cfg: C{str}
    '''
    if not cfg in self._cfgs:
      self._cfgs.append(cfg)
      self.updateDisplayedConfig()

  def remConfig(self, cfg):
    '''
    Remove the given configurations from the node.
    @param cfg: the loaded configuration, which contains this node.
    @type cfg: C{str}
    '''
    if cfg in self._cfgs:
      self._cfgs.remove(cfg)
    if self.is_valid():
      self.updateDisplayedConfig()

  def updateDisplayedConfig(self):
    '''
    Updates the configuration representation in other column.
    '''
    if not self.parent_item is None:
      cfg_col = self.parent_item.child(self.row(), NodeItem.COL_CFG)
      if not cfg_col is None and isinstance(cfg_col, QtGui.QStandardItem):
        cfg_col.setText(str(''.join(['[',str(len(self._cfgs)),']'])) if len(self._cfgs) > 1 else "")
        # set tooltip
        tooltip = ''
        if len(self._cfgs) > 0:
          tooltip = ''
          if len(self._cfgs) > 0:
            tooltip = ''.join([tooltip, '<h4>', 'Configurations:', '</h4><dl>'])
            for c in self._cfgs:
              if NodeItem.is_default_cfg(c):
                tooltip = ''.join([tooltip, '<dt>[default]', c[0], '</dt>'])
              else:
                tooltip = ''.join([tooltip, '<dt>', c, '</dt>'])
            tooltip = ''.join([tooltip, '</dl>'])
        cfg_col.setToolTip(''.join(['<div>', tooltip, '</div>']))
        # set icons
        has_launches = NodeItem.has_launch_cfgs(self._cfgs)
        has_defaults = NodeItem.has_default_cfgs(self._cfgs)
        if has_launches and has_defaults:
          cfg_col.setIcon(QtGui.QIcon(':/icons/crystal_clear_launch_file_def_cfg.png'))
        elif has_launches:
          cfg_col.setIcon(QtGui.QIcon(':/icons/crystal_clear_launch_file.png'))
        elif has_defaults:
          cfg_col.setIcon(QtGui.QIcon(':/icons/default_cfg.png'))
        else:
          cfg_col.setIcon(QtGui.QIcon())
        if isinstance(self.parent_item, GroupItem):
          self.parent_item.updateDisplayedConfig()

  def type(self):
    return NodeItem.ITEM_TYPE

  @classmethod
  def newNodeRow(self, name, masteruri):
    '''
    Creates a new node row and returns it as a list with items. This list is 
    used for the visualization of node data as a table row.
    @param name: the node name
    @type name: C{str}
    @param masteruri: the URI or the ROS master assigned to this node.
    @type masteruri: C{str}
    @return: the list for the representation as a row
    @rtype: C{[L{NodeItem}, L{PySide.QtGui.QStandardItem}(Cofigurations), L{PySide.QtGui.QStandardItem}(Node URI)]}
    '''
    items = []
    item = NodeItem(NodeInfo(name, masteruri))
    items.append(item)
    cfgitem = QtGui.QStandardItem()
    items.append(cfgitem)
#    uriitem = QtGui.QStandardItem()
#    items.append(uriitem)
    return items

  @classmethod
  def has_launch_cfgs(cls, cfgs):
    for c in cfgs:
      if not cls.is_default_cfg(c):
        return True
    return False

  @classmethod
  def has_default_cfgs(cls, cfgs):
    for c in cfgs:
      if cls.is_default_cfg(c):
        return True
    return False

  @classmethod
  def is_default_cfg(cls, cfg):
    return isinstance(cfg, tuple)

  @classmethod
  def toHTML(cls, node_name):
    '''
    Creates a HTML representation of the node name.
    @param node_name: the name of the node
    @type node_name: C{str}
    @return: the HTML representation of the name of the node
    @rtype: C{str}
    '''
    ns, sep, name = node_name.rpartition('/')
    result = ''
    if sep:
      result = ''.join(['<div>', '<span style="color:gray;">', str(ns), sep, '</span><b>', name, '</b></div>'])
    else:
      result = name
    return result

  def __eq__(self, item):
    '''
    Compares the name of the node.
    '''
    if isinstance(item, str) or isinstance(item, unicode):
      return self.name.lower() == item.lower()
    elif not (item is None):
      return self.name.lower() == item.name.lower()
    return False

  def __gt__(self, item):
    '''
    Compares the name of the node.
    '''
    if isinstance(item, str) or isinstance(item, unicode):
      return self.name.lower() > item.lower()
    elif not (item is None):
      return self.name.lower() > item.name.lower()
    return False


################################################################################
##############                NodeTreeModel                       ##############
################################################################################

class NodeTreeModel(QtGui.QStandardItemModel):
  '''
  The model to show the nodes running in a ROS system or loaded by a launch
  configuration.
  '''
#  ICONS = {'default'        : QtGui.QIcon(),
#           'run'            : QtGui.QIcon(":/icons/state_run.png"),
#           'warning'        : QtGui.QIcon(":/icons/crystal_clear_warning.png"),
#           'def_launch_cfg' : QtGui.QIcon(":/icons/crystal_clear_launch_file_def_cfg.png"),
#           'launch_cfg'     : QtGui.QIcon(":/icons/crystal_clear_launch_file.png"),
#           'def_cfg'        : QtGui.QIcon(":/icons/default_cfg.png") }
  
  header = [('Name', 450),
            ('Cfgs', -1)]
#            ('URI', -1)]

  hostInserted = QtCore.Signal(HostItem)
  '''@ivar: the Qt signal, which is emitted, if a new host was inserted. 
  Parameter: L{QtCore.QModelIndex} of the inserted host item'''

  def __init__(self, host_address, masteruri, parent=None):
    '''
    Initialize the model.
    '''
    super(NodeTreeModel, self).__init__(parent)
    self.setColumnCount(len(NodeTreeModel.header))
    self.setHorizontalHeaderLabels([label for label, width in NodeTreeModel.header])
    self._local_host_address = host_address

  @property
  def local_addr(self):
    return self._local_host_address

  def flags(self, index):
    if not index.isValid():
      return QtCore.Qt.NoItemFlags
    return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
  
  def getHostItem(self, address):
    '''
    Searches for the host item in the model. If no item is found a new one will 
    created and inserted in sorted order.
    @param address: used in case of creation a new host item 
    @type address: C{str}
    @return: the item associated with the given master
    @rtype: L{HostItem}
    '''
    host = address
    if not host:
      host = self.local_addr
    local = (self.local_addr == host)

    # find the host item by address
    root = self.invisibleRootItem()
    for i in range(root.rowCount()):
      if root.child(i) == host:
        return root.child(i)
      elif root.child(i) > host:
        hostItem = HostItem(address, local)
        self.insertRow(i, hostItem)
        self.hostInserted.emit(hostItem)
        return hostItem
    hostItem = HostItem(address, local)
    self.appendRow(hostItem)
    self.hostInserted.emit(hostItem)
    return hostItem

  def updateModelData(self, nodes):
    '''
    Updates the model data.
    @param nodes: a dictionary with name and info objects of the nodes.
    @type nodes: C{dict(str:L{NodeInfo}, ...)}
    '''
    # separate into different hosts
    hosts = dict()
    for (name, node) in nodes.items():
      host = nm.nameres().getHostname(node.uri if not node.uri is None else node.masteruri)
      if not hosts.has_key(host):
        hosts[host] = dict()
      hosts[host][name] = node
    # update nodes for each host
    for (host, nodes_filtered) in hosts.items():
      hostItem = self.getHostItem(host)
      # rename the host item if needed
      host_name = nm.nameres().getName(host=host)
      if host_name and not (hostItem.name == host_name):
        hostItem.name = host_name
      hostItem.updateRunningNodeState(nodes_filtered)
    # update nodes of the hosts, which are not more exists
    for i in reversed(range(self.invisibleRootItem().rowCount())):
      host = self.invisibleRootItem().child(i)
      if not hosts.has_key(host.address):
        host.updateRunningNodeState({})
    self.removeEmptyHosts()
    # update the duplicate state
#    self.markNodesAsDuplicateOf(self.getRunningNodes())

  def addCapabilities(self, host_address, cfg, capabilities):
    '''
    Adds groups to the model
    @param host_address: the address the host
    @type host_address: C{str}
    @param cfg: the configuration name (launch file name or tupel for default configuration)
    @type cfg: C{str or (str, str))} 
    @param capabilities: the structure for capabilities
    @type capabilities: C{dict(namespace: dict(group:dict('type' : str, 'description' : str, 'nodes' : [str])))} 
    '''
    hostItem = self.getHostItem(host_address)
    hostItem.addCapabilities(cfg, capabilities, host_address)
    self.removeEmptyHosts()
    
  def appendConfigNodes(self, host_address, nodes):
    '''
    Adds nodes to the model. If the node is already in the model, only his 
    configuration list will be extended.
    @param host_address: the address the host
    @type host_address: C{str}
    @param nodes: a dictionary with node names and their configurations
    @type nodes: C{dict(str : str)} 
    '''
    hostItem = self.getHostItem(host_address)
    for (name, cfg) in nodes.items():
      items = hostItem.getNodeItemsByName(name)
      for item in items:
        item.addConfig(cfg)
      if not items:
        # create the new node
        masteruri = nm.nameres().getUri(host=host_address)
        node_info = NodeInfo(name, masteruri)
        hostItem.addNode(node_info, cfg)
    self.removeEmptyHosts()
    # update the duplicate state
#    self.markNodesAsDuplicateOf(self.getRunningNodes())

  def removeConfigNodes(self, cfg):
    '''
    Removes nodes from the model. If node is running or containing in other
    launch or default configurations , only his configuration list will be 
    reduced.
    @param cfg: the name of the confugration to close
    @type cfg: C{str} 
    '''
    for i in reversed(range(self.invisibleRootItem().rowCount())):
      host = self.invisibleRootItem().child(i)
      items = host.getNodeItems()
      for item in items:
        item.remConfig(cfg)
      host.remCapablities(cfg)
      host.clearUp()
      if host.rowCount() == 0:
        self.invisibleRootItem().removeRow(i)

  def removeEmptyHosts(self):
    # remove empty hosts
    for i in reversed(range(self.invisibleRootItem().rowCount())):
      host = self.invisibleRootItem().child(i)
      if host.rowCount() == 0:
        self.invisibleRootItem().removeRow(i)

  def isDuplicateNode(self, node_name):
    for i in reversed(range(self.invisibleRootItem().rowCount())):
      host = self.invisibleRootItem().child(i)
      if not host is None: # should not occur
        nodes = host.getNodeItemsByName(node_name)
        for n in nodes:
          if n.has_running:
            return True
    return False

  def getRunningNodes(self):
    '''
    Returns a list with all known running nodes.
    @rtype: C{[str]}
    '''
    running_nodes = list()
    ## determine all running nodes
    for i in reversed(range(self.invisibleRootItem().rowCount())):
      host = self.invisibleRootItem().child(i)
      if not host is None: # should not occur
        running_nodes[len(running_nodes):] = host.getRunningNodes()
    return running_nodes

  def markNodesAsDuplicateOf(self, running_nodes):
    '''
    If there are a synchronization running, you have to avoid to running the 
    node with the same name on different hosts. This method helps to find the 
    nodes with same name running on other hosts and loaded by a configuration.
    The nodes loaded by a configuration will be inform about a currently running
    nodes, so a warning can be displayed!
    @param running_nodes: A list with node names, which are running on other hosts.
    @type running_nodes: C{[str]}
    '''
    for i in reversed(range(self.invisibleRootItem().rowCount())):
      host = self.invisibleRootItem().child(i)
      if not host is None: # should not occur
        host.markNodesAsDuplicateOf(running_nodes)

  def updateHostDescription(self, host, descr_type, descr_name, descr):
    '''
    Updates the description of a host.
    @param host: host to update
    @type host: C{str}
    @param descr_type: the type of the robot
    @type descr_type: C{str}
    @param descr_name: the name of the robot
    @type descr_name: C{str}
    @param descr: the description of the robot as a U{http://docutils.sourceforge.net/rst.html|reStructuredText} 
    @type descr: C{str}
    '''
    root = self.invisibleRootItem()
    for i in range(root.rowCount()):
      if root.child(i) == host:
        h = root.child(i)
        h.updateDescription(descr_type, descr_name, descr)
        return h.updateTooltip()
