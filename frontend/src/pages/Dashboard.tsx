import { useEffect, useState } from 'react'
import { Row, Col, Card, Statistic, Tag, List, Spin, Empty } from 'antd'
import {
  FileTextOutlined,
  RiseOutlined,
  MessageOutlined,
  AlertOutlined
} from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import dayjs from 'dayjs'
import { statisticsAPI, hotTopicsAPI } from '../services/api'

interface StatData {
  total: number
  positive: number
  negative: number
  neutral: number
}

export default function Dashboard() {
  const [loading, setLoading] = useState(true)
  const [statData, setStatData] = useState<StatData>({
    total: 0,
    positive: 0,
    negative: 0,
    neutral: 0
  })
  const [hotTopics, setHotTopics] = useState<any[]>([])
  const [sourceData, setSourceData] = useState<Record<string, number>>({})
  const [trendData, setTrendData] = useState<any[]>([])

  useEffect(() => {
    fetchDashboardData()
  }, [])

  const fetchDashboardData = async () => {
    setLoading(true)
    try {
      const [sentimentRes, topicsRes, sourcesRes, trendRes] = await Promise.all([
        statisticsAPI.getSentiment(24),
        hotTopicsAPI.list(10, 24),
        statisticsAPI.getSources(24),
        statisticsAPI.getTrend(24)
      ])

      if (sentimentRes.success) {
        const data = sentimentRes.data
        setStatData({
          total: Object.values(data).reduce((a: number, b: any) => a + b, 0) as number,
          positive: data.positive || 0,
          negative: data.negative || 0,
          neutral: data.neutral || 0
        })
      }

      if (topicsRes) {
        setHotTopics(topicsRes)
      }

      if (sourcesRes.success) {
        setSourceData(sourcesRes.data)
      }

      if (trendRes.success) {
        setTrendData(trendRes.data || [])
      }
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error)
    } finally {
      setLoading(false)
    }
  }

  const getSentimentChartOption = () => ({
    tooltip: { trigger: 'item' },
    legend: { bottom: '5%', left: 'center' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
      label: { show: false },
      emphasis: { label: { show: true, fontSize: 14, fontWeight: 'bold' } },
      data: [
        { value: statData.positive, name: '正面', itemStyle: { color: '#52c41a' } },
        { value: statData.negative, name: '负面', itemStyle: { color: '#ff4d4f' } },
        { value: statData.neutral, name: '中性', itemStyle: { color: '#faad14' } }
      ]
    }]
  })

  const getSourceChartOption = () => {
    const data = Object.entries(sourceData).map(([name, value]) => ({ name, value }))
    return {
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      xAxis: { type: 'category', data: data.map(d => d.name) },
      yAxis: { type: 'value' },
      series: [{
        data: data.map(d => d.value),
        type: 'bar',
        itemStyle: { color: '#1890ff' }
      }]
    }
  }

  const getTrendChartOption = () => {
    const hourlyData: Record<string, number> = {}
    trendData.forEach((item: any) => {
      const hour = dayjs(item.time).format('MM-DD HH:00')
      hourlyData[hour] = (hourlyData[hour] || 0) + 1
    })

    const sortedHours = Object.keys(hourlyData).sort()

    return {
      tooltip: { trigger: 'axis' },
      xAxis: {
        type: 'category',
        data: sortedHours,
        axisLabel: { rotate: 45 }
      },
      yAxis: { type: 'value' },
      series: [{
        data: sortedHours.map(h => hourlyData[h]),
        type: 'line',
        smooth: true,
        areaStyle: { opacity: 0.3 },
        itemStyle: { color: '#1890ff' }
      }]
    }
  }

  if (loading) {
    return (
      <div className="loading-container">
        <Spin size="large" />
      </div>
    )
  }

  return (
    <div>
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="舆情总量"
              value={statData.total}
              prefix={<FileTextOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="正面舆情"
              value={statData.positive}
              valueStyle={{ color: '#52c41a' }}
              prefix={<RiseOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="负面舆情"
              value={statData.negative}
              valueStyle={{ color: '#ff4d4f' }}
              prefix={<AlertOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="热点话题"
              value={hotTopics.length}
              valueStyle={{ color: '#1890ff' }}
              prefix={<MessageOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={12}>
          <Card title="情感分布">
            <ReactECharts option={getSentimentChartOption()} style={{ height: 300 }} />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="来源分布">
            <ReactECharts option={getSourceChartOption()} style={{ height: 300 }} />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={16}>
          <Card title="舆情趋势">
            <ReactECharts option={getTrendChartOption()} style={{ height: 300 }} />
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title="热点话题">
            {hotTopics.length > 0 ? (
              <List
                dataSource={hotTopics}
                renderItem={(item: any) => (
                  <List.Item>
                    <Tag color={item.is_hot ? 'red' : 'blue'}>
                      {item.keyword}
                    </Tag>
                    <span style={{ marginLeft: 8 }}>{item.frequency} 次</span>
                  </List.Item>
                )}
              />
            ) : (
              <Empty description="暂无热点话题" />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  )
}
