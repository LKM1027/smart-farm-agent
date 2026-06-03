import { defineStore } from 'pinia'
import axios from 'axios'

function randFloat(min, max, dp = 1) {
  return parseFloat((Math.random() * (max - min) + min).toFixed(dp))
}

function randHex() {
  return Math.floor(Math.random() * 256).toString(16).toUpperCase().padStart(2, '0')
}

function buildFallbackResponse(query) {
  const hasSensor = /온도|습도|상태|환경|얼마나|어때|co2|알려줘/i.test(query) || Math.random() > 0.5
  const hasRag = /어떻게|방법|방제|대처|알려줘/i.test(query)

  const sensorData = hasSensor ? {
    facility_id: 'DEMO-FACILITY-001',
    temperature: randFloat(22, 30),
    humidity: randFloat(60, 92),
    co2: Math.round(randFloat(380, 800)),
    updated_at: new Date().toISOString(),
  } : null

  const controlSeq = hasSensor ? [
    {
      device: 'CC18',
      action: 'SET_LV',
      value: randFloat(40, 80),
      description: '환풍기 출력 조절',
    },
    {
      device: 'CC01',
      action: 'OPEN',
      value: null,
      description: '천창 개방',
    },
  ] : null

  const answer = hasSensor
    ? `실시간 센서 관제 결과, 온도 **${sensorData.temperature}℃**, 습도 **${sensorData.humidity}%**, CO2 **${sensorData.co2}ppm**로 확인되었습니다.`
    : '현재 데모 응답을 생성했습니다.'

  return {
    intents: { is_sensor_needed: hasSensor, is_rag_needed: hasRag },
    sensor_data: sensorData,
    control_sequence: controlSeq,
    answer,
    modbus_frames: hasSensor ? [
      '[SYS] KS X 3267:2022 Modbus RTU Protocol Translator initialized',
      '[SYS] RS485 2-Wire Half-Duplex / Baud: 19200 / Parity: Even',
      `[SYS] ${(controlSeq?.length ?? 0)} command(s) queued for transmission`,
      '[CMD 01] device=CC18 action=SET_LV value=65.0',
      `[Tx] 05 06 03 12 00 41 ${randHex()} ${randHex()}`,
      `[Rx] 05 06 03 12 00 41 ${randHex()} ${randHex()}  ACK`,
      '[CMD 02] device=CC01 action=OPEN value=null',
      `[Tx] 01 06 03 00 00 01 ${randHex()} ${randHex()}`,
      `[Rx] 01 06 03 00 00 01 ${randHex()} ${randHex()}  ACK`,
      '[SYS] Transmission complete. All commands dispatched.',
    ] : null,
  }
}

export const useAgentStore = defineStore('agent', {
  state: () => ({
    isPageLoading: false,
    intents: {
      is_sensor_needed: false,
      is_rag_needed: false,
    },
    sensorData: null,
    controlSequence: null,
    modbusFrames: [],
    answer: '',
    chatHistory: [],
    reports: {
      farmReport: '',
      equipmentReport: '',
      isLoading: false,
    },
    // ── 주간 리포트 아카이브 ──
    weeklyReports: [],
    selectedReport: null,
    isLoadingReports: false,
    isGeneratingReport: false,
    reportError: null,
    // ─────────────────────
    simulationNotice: '',
    isInjectingAnomaly: false,
    isFallbackMode: false,
    answerSource: '', // RAG, LLM_PARAMETRIC, LLM_ERROR 등
    lastError: null,
  }),

  getters: {
    isSensorActive: (s) => s.isPageLoading && s.intents.is_sensor_needed,
    isRagActive: (s) => s.isPageLoading && s.intents.is_rag_needed,
    hasControlData: (s) => Array.isArray(s.controlSequence) && s.controlSequence.length > 0,
    hasSensorData: (s) => s.sensorData !== null,
  },

  actions: {
    _resetData() {
      this.intents = { is_sensor_needed: false, is_rag_needed: false }
      this.controlSequence = null
      this.modbusFrames = []
      this.answer = ''
      this.answerSource = ''
      this.lastError = null
      this.isFallbackMode = false
    },

    _applyResponse(data) {
      this.intents = data.intents ?? this.intents
      this.sensorData = data.sensor_data ?? this.sensorData
      // 백엔드의 'reason'을 프론트엔드에서 일관되게 처리 (필요시 mapping)
      this.controlSequence = data.control_sequence ?? null
      this.modbusFrames = data.modbus_frames ?? []
      this.answer = data.answer ?? ''
      this.answerSource = data.answer_source ?? ''
    },

    async sendAgentQuery(text) {
      if (!text) return

      this._resetData()
      this.isPageLoading = true
      this.chatHistory.push({
        role: 'user',
        text,
        timestamp: new Date(),
      })

      try {
        const response = await axios.post(
          'http://localhost:8000/api/v1/agent/chat',
          { query: text },
          { timeout: 60000, headers: { 'Content-Type': 'application/json' } },
        )

        this._applyResponse(response.data)
        await this._simulateStageDelay()
      } catch (err) {
        console.warn('[AgentStore] API failed, using fallback data:', err?.message)
        this.lastError = err?.message ?? 'Unknown error'
        this.isFallbackMode = true

        const fallback = buildFallbackResponse(text)
        this.intents = fallback.intents

        await this._simulateStageDelay()
        this._applyResponse(fallback)
      }

      this.chatHistory.push({
        role: 'agent',
        text: this.answer,
        isFallback: this.isFallbackMode,
        answerSource: this.answerSource,
        timestamp: new Date(),
      })

      this.isPageLoading = false
    },

    async _simulateStageDelay() {
      const stages = [
        this.intents.is_sensor_needed,
        this.intents.is_rag_needed,
      ].filter(Boolean).length

      const delay = Math.max(1500, stages * 1200)
      await new Promise((resolve) => setTimeout(resolve, delay))
    },

    async generateWeeklyReport() {
      this.reports.isLoading = true
      this.reports.farmReport = ''
      this.reports.equipmentReport = ''
      this.lastError = null

      try {
        const response = await axios.get(
          'http://localhost:8000/api/v1/report/generate',
          { timeout: 30000 },
        )

        this.reports.farmReport = response.data.farm_report || ''
        this.reports.equipmentReport = response.data.equipment_report || ''
      } catch (err) {
        console.error('[AgentStore] report generation failed:', err?.message)
        this.lastError = err?.message ?? 'Unknown error'
        this.reports.farmReport = '리포트 생성 중 오류가 발생했습니다.'
        this.reports.equipmentReport = '리포트 생성 중 오류가 발생했습니다.'
      } finally {
        this.reports.isLoading = false
      }
    },

    async fetchLatestSensorData() {
      try {
        const response = await axios.get('/api/test/sensor/latest', { timeout: 10000 })
        const data = response.data ?? {}

        if (data.temperature == null && data.humidity == null && data.co2 == null) return

        this.sensorData = {
          facility_id: data.facility_id ?? 'N/A',
          temperature: data.temperature,
          humidity: data.humidity,
          co2: data.co2,
          updated_at: data.timestamp ?? new Date().toISOString(),
        }
      } catch (err) {
        this.lastError = err?.message ?? 'Unknown error'
      }
    },

    async injectHeatwaveAnomaly() {
      if (this.isInjectingAnomaly) return

      this.isInjectingAnomaly = true
      this.lastError = null
      this.simulationNotice = ''

      try {
        const response = await axios.post('/api/test/inject-anomaly')
        const agentMessage = response.data?.agent_message ?? ''

        this.sensorData = {
          facility_id: 'FAULT-INJECTION-DEMO',
          temperature: 45.5,
          humidity: 40.0,
          co2: 200,
          updated_at: new Date().toISOString(),
        }
        this.intents = { is_sensor_needed: true, is_rag_needed: true }
        this.controlSequence = [
          {
            device: 'CC18',
            action: 'ON',
            value: null,
            description: 'Heatwave fault injection exhaust fan start',
          },
          {
            device: 'CC01',
            action: 'OPEN',
            value: null,
            description: 'Roof vent open for heat exhaust',
          },
          {
            device: 'CC02',
            action: 'OPEN',
            value: null,
            description: 'Side vent open for heat exhaust',
          },
        ]
        this.modbusFrames = [
          '[SYS] KS X 3267:2022 Modbus RTU Protocol Translator initialized',
          '[SYS] RS485 2-Wire Half-Duplex / Baud: 19200 / Parity: Even',
          '[SYS] 3 command(s) queued for transmission',
          '[CMD 01] device=CC18 action=ON value=null',
          '[Tx] 05 06 03 12 00 01 E9 CF',
          '[Rx] 05 06 03 12 00 01 E9 CF  ACK',
          '[CMD 02] device=CC01 action=OPEN value=null',
          '[Tx] 01 06 03 00 00 01 48 4E',
          '[Rx] 01 06 03 00 00 01 48 4E  ACK',
          '[CMD 03] device=CC02 action=OPEN value=null',
          '[Tx] 02 06 03 00 00 01 48 7D',
          '[Rx] 02 06 03 00 00 01 48 7D  ACK',
          '[SYS] Transmission complete. All commands dispatched.',
        ]
        this.answer = agentMessage

        if (agentMessage) {
          this.chatHistory.push({
            role: 'agent',
            text: agentMessage,
            timestamp: new Date(),
          })
          this.simulationNotice = agentMessage
        }
      } catch (err) {
        this.lastError = err?.message ?? 'Unknown error'
        this.simulationNotice = 'Anomaly injection failed.'
      } finally {
        this.isInjectingAnomaly = false
      }
    },

    // ─────────────────────────────────────────
    // 주간 리포트 아카이브 액션
    // ─────────────────────────────────────────

    /**
     * GET /api/reports → 저장된 리포트 목록을 로드하여 weeklyReports에 저장
     */
    async fetchWeeklyReports() {
      this.isLoadingReports = true
      this.reportError = null
      try {
        const response = await axios.get('http://localhost:8000/api/reports', { timeout: 15000 })
        this.weeklyReports = response.data ?? []
        if (this.weeklyReports.length > 0 && !this.selectedReport) {
          this.selectedReport = this.weeklyReports[0]
        }
      } catch (err) {
        console.error('[AgentStore] fetchWeeklyReports failed:', err?.message)
        this.reportError = err?.message ?? '리포트 목록을 불러올 수 없습니다.'
      } finally {
        this.isLoadingReports = false
      }
    },

    /**
     * POST /api/reports/generate → 새 리포트 생성 후 목록 재로드
     */
    async generateWeeklyReportToArchive() {
      if (this.isGeneratingReport) return
      this.isGeneratingReport = true
      this.reportError = null
      try {
        await axios.post('http://localhost:8000/api/reports/generate', null, { timeout: 120000 })
        // 생성 완료 후 목록 재로드
        await this.fetchWeeklyReports()
      } catch (err) {
        console.error('[AgentStore] generateWeeklyReportToArchive failed:', err?.message)
        this.reportError = err?.message ?? '리포트 생성에 실패했습니다.'
      } finally {
        this.isGeneratingReport = false
      }
    },

    /**
     * 리스트에서 리포트 선택
     */
    selectReport(report) {
      this.selectedReport = report
    },
  },
})
