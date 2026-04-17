import { useState } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { Layout, Menu, theme } from 'antd'
import {
  DashboardOutlined,
  SearchOutlined,
  MessageOutlined,
  FileTextOutlined,
  SettingOutlined
} from '@ant-design/icons'

const { Sider, Content, Header } = Layout

const menuItems = [
  {
    key: '/dashboard',
    icon: <DashboardOutlined />,
    label: '数据概览'
  },
  {
    key: '/search',
    icon: <SearchOutlined />,
    label: '舆情检索'
  },
  {
    key: '/chat',
    icon: <MessageOutlined />,
    label: '智能问答'
  },
  {
    key: '/briefing',
    icon: <FileTextOutlined />,
    label: '简报生成'
  },
  {
    key: '/settings',
    icon: <SettingOutlined />,
    label: '系统设置'
  }
]

export default function MainLayout() {
  const [collapsed, setCollapsed] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const { token: { colorBgContainer } } = theme.useToken()

  const handleMenuClick = ({ key }: { key: string }) => {
    navigate(key)
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        theme="dark"
      >
        <div className="logo">
          {collapsed ? '舆' : '舆情通'}
        </div>
        <Menu
          theme="dark"
          selectedKeys={[location.pathname]}
          mode="inline"
          items={menuItems}
          onClick={handleMenuClick}
        />
      </Sider>
      <Layout>
        <Header style={{
          padding: '0 24px',
          background: colorBgContainer,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
          <h2 style={{ margin: 0 }}>
            {menuItems.find(item => item.key === location.pathname)?.label || '舆情通'}
          </h2>
        </Header>
        <Content style={{ margin: '16px' }}>
          <div style={{
            padding: 24,
            minHeight: 360,
            background: colorBgContainer,
            borderRadius: 8
          }}>
            <Outlet />
          </div>
        </Content>
      </Layout>
    </Layout>
  )
}
