import { Card, Form, Input, InputNumber, Switch, Button, message, Divider, Space, Alert } from 'antd'
import { SaveOutlined, ReloadOutlined } from '@ant-design/icons'

export default function Settings() {
  const [form] = Form.useForm()

  const handleSave = () => {
    message.success('设置已保存')
  }

  const handleReset = () => {
    form.resetFields()
    message.info('设置已重置')
  }

  return (
    <div>
      <Alert
        message="系统配置"
        description="以下配置项需要重启服务后生效"
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />

      <Card title="API配置">
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            apiHost: '0.0.0.0',
            apiPort: 8000,
            debug: true
          }}
        >
          <Form.Item name="apiHost" label="API Host">
            <Input placeholder="0.0.0.0" />
          </Form.Item>
          <Form.Item name="apiPort" label="API Port">
            <InputNumber min={1} max={65535} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="debug" label="调试模式" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Card>

      <Card title="LLM配置" style={{ marginTop: 16 }}>
        <Form layout="vertical">
          <Form.Item label="OpenAI API Key">
            <Input.Password placeholder="sk-..." />
          </Form.Item>
          <Form.Item label="API Base URL (可选)">
            <Input placeholder="https://api.openai.com/v1" />
          </Form.Item>
          <Form.Item label="模型名称">
            <Input placeholder="gpt-3.5-turbo" />
          </Form.Item>
        </Form>
      </Card>

      <Card title="检索配置" style={{ marginTop: 16 }}>
        <Form layout="vertical">
          <Form.Item label="Embedding模型">
            <Input placeholder="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2" />
          </Form.Item>
          <Form.Item label="Reranker模型">
            <Input placeholder="BAAI/bge-reranker-base" />
          </Form.Item>
          <Form.Item label="向量维度">
            <InputNumber value={384} style={{ width: '100%' }} disabled />
          </Form.Item>
          <Form.Item label="默认返回数量">
            <InputNumber min={1} max={50} value={5} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Card>

      <Card title="数据库配置" style={{ marginTop: 16 }}>
        <Form layout="vertical">
          <Form.Item label="PostgreSQL Host">
            <Input placeholder="postgres" />
          </Form.Item>
          <Form.Item label="PostgreSQL Port">
            <InputNumber value={5432} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item label="数据库名称">
            <Input placeholder="yuqing_db" />
          </Form.Item>
          <Divider />
          <Form.Item label="Redis Host">
            <Input placeholder="redis" />
          </Form.Item>
          <Form.Item label="Redis Port">
            <InputNumber value={6379} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Card>

      <Card title="爬虫配置" style={{ marginTop: 16 }}>
        <Form layout="vertical">
          <Form.Item label="请求超时(秒)">
            <InputNumber min={5} max={120} value={30} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item label="最大重试次数">
            <InputNumber min={1} max={10} value={3} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item label="并发限制">
            <InputNumber min={1} max={20} value={5} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Card>

      <div style={{ marginTop: 16, textAlign: 'right' }}>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={handleReset}>
            重置
          </Button>
          <Button type="primary" icon={<SaveOutlined />} onClick={handleSave}>
            保存设置
          </Button>
        </Space>
      </div>
    </div>
  )
}
