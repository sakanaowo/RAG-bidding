# RAG-Bidding System Upgrade Plan
## Kế hoạch nâng cấp hệ thống để thống nhất format pipeline

**Tác giả**: Development Team  
**Ngày tạo**: 30/10/2025  
**Phiên bản**: 1.0  
**Trạng thái**: Đang chờ phê duyệt  

---

## 📋 Tổng quan dự án

### Vấn đề hiện tại
- **Nguyên nhân gốc**: Hệ thống hiện tại sử dụng 4 pipeline riêng biệt (bidding, circular, law, decree) với metadata schema khác nhau
- **File gốc**: `processed_chunks.jsonl` được tạo bởi OptimalLegalChunker (kiến trúc monolithic cũ)
- **Pipeline hiện tại**: Kiến trúc modular mới với các stage riêng biệt (extract→clean→parse→chunk→map)
- **Tình trạng**: 55 trường metadata độc nhất, không có trường chung nào giữa 4 pipeline

### Mục tiêu dự án
1. **Thống nhất schema metadata** giữa tất cả pipeline
2. **Đảm bảo tương thích** với hệ thống embedding hiện tại
3. **Duy trì chất lượng** dữ liệu và hiệu suất hệ thống
4. **Migration an toàn** dữ liệu hiện có

---

## 🎯 Chiến lược triển khai

### Option A: Khôi phục OptimalLegalChunker
- **Ưu điểm**: Tái tạo chính xác format gốc
- **Nhược điểm**: Quay lại kiến trúc cũ, mất tính modular
- **Timeline**: 2-3 tuần
- **Không khuyến nghị**: Bước lùi về mặt kiến trúc

### Option B: Compatibility Layer
- **Ưu điểm**: Giữ kiến trúc hiện tại, thêm layer chuyển đổi
- **Nhược điểm**: Phức tạp hóa hệ thống, hiệu suất giảm
- **Timeline**: 3-4 tuần
- **Phù hợp**: Giải pháp tạm thời

### **Option C: Complete Upgrade (KHUYẾN NGHỊ)**
- **Ưu điểm**: Hệ thống thống nhất, hiệu suất tối ưu, bảo trì dễ dàng
- **Nhược điểm**: Thời gian triển khai dài
- **Timeline**: 9-14 tuần
- **Lựa chọn tốt nhất**: Giải pháp dài hạn

---

## 📅 Timeline tổng thể

```
Tháng 1: Phase 1 (Tuần 1-3)
Tháng 2: Phase 2 (Tuần 4-6) + Phase 3 (Tuần 7-9)
Tháng 3: Phase 4 (Tuần 10-12) + Phase 5 (Tuần 13-14)
```

**Tổng thời gian**: 14 tuần (3.5 tháng)

---

## 🚀 Phase 1: Schema Standardization
**Timeline**: 3 tuần  
**Mục tiêu**: Thiết kế và thống nhất metadata schema

### Week 1: Analysis & Design
#### Ngày 1-2: Deep Analysis
- [ ] Phân tích chi tiết 55 trường metadata hiện có
- [ ] Mapping relationship giữa các trường tương đương
- [ ] Xác định trường bắt buộc vs optional

#### Ngày 3-5: Schema Design
- [ ] Thiết kế unified schema với 21 core fields:
  ```json
  {
    "document_info": {
      "id": "string",
      "title": "string", 
      "doc_type": "enum",
      "source": "string",
      "url": "string"
    },
    "legal_metadata": {
      "issued_by": "string",
      "effective_date": "date",
      "status": "enum", 
      "legal_level": "enum",
      "subject_area": "array"
    },
    "content_structure": {
      "section": "string",
      "article": "string", 
      "paragraph": "string",
      "hierarchy_level": "integer"
    },
    "processing_metadata": {
      "chunk_id": "string",
      "chunk_index": "integer",
      "processing_date": "datetime",
      "pipeline_version": "string"
    },
    "quality_metrics": {
      "text_length": "integer",
      "confidence_score": "float"
    }
  }
  ```

### Week 2: Validation & Refinement
#### Ngày 1-3: Schema Validation
- [ ] Tạo test cases cho schema mới
- [ ] Validate với dữ liệu mẫu từ 4 pipeline
- [ ] Performance testing cho schema complexity

#### Ngày 4-5: Stakeholder Review
- [ ] Present schema design cho team
- [ ] Collect feedback và requirements bổ sung
- [ ] Finalize schema specification

### Week 3: Documentation & Approval
#### Ngày 1-2: Documentation
- [ ] Tạo comprehensive schema documentation
- [ ] Migration mapping guide (old → new fields)
- [ ] API impact analysis

#### Ngày 3-5: Testing Framework
- [ ] Tạo validation rules cho schema mới
- [ ] Unit tests cho schema compliance
- [ ] Integration test framework setup

**Deliverables Phase 1**:
- ✅ Unified metadata schema specification
- ✅ Field mapping documentation  
- ✅ Validation framework
- ✅ Test cases và benchmarks

---

## 🔧 Phase 2: Pipeline Code Updates
**Timeline**: 3 tuần  
**Mục tiêu**: Cập nhật 4 pipeline để sử dụng unified schema

### Week 4: Bidding & Circular Pipelines
#### Ngày 1-2: Bidding Pipeline Update
- [ ] Update `src/preprocessing/metadata/bidding_mapper.py`
- [ ] Implement new schema mapping logic
- [ ] Update processing statistics
- [ ] Unit testing

#### Ngày 3-5: Circular Pipeline Update
- [ ] Update `src/preprocessing/metadata/circular_mapper.py`
- [ ] Implement new schema mapping logic
- [ ] Handle circular-specific fields
- [ ] Integration testing

### Week 5: Law & Decree Pipelines
#### Ngày 1-2: Law Pipeline Update
- [ ] Update `src/preprocessing/metadata/law_mapper.py`
- [ ] Implement new schema mapping logic
- [ ] Handle legal document complexity
- [ ] Unit testing

#### Ngày 3-5: Decree Pipeline Update
- [ ] Update `src/preprocessing/metadata/decree_mapper.py`
- [ ] Implement new schema mapping logic
- [ ] Handle decree-specific requirements
- [ ] Integration testing

### Week 6: Pipeline Integration
#### Ngày 1-3: End-to-End Testing
- [ ] Test all 4 pipelines với data thực
- [ ] Validate output format consistency
- [ ] Performance benchmarking
- [ ] Memory usage optimization

#### Ngày 4-5: Quality Assurance
- [ ] Regression testing
- [ ] Output quality validation
- [ ] Error handling improvement
- [ ] Documentation updates

**Deliverables Phase 2**:
- ✅ Updated pipeline code (4 pipelines)
- ✅ Unit tests cho mỗi pipeline
- ✅ Integration test suite
- ✅ Performance benchmarks

---

## 💾 Phase 3: Data Migration
**Timeline**: 3 tuần  
**Mục tiêu**: Migration dữ liệu hiện có sang format mới

### Week 7: Migration Strategy
#### Ngày 1-2: Data Assessment
- [ ] Inventory tất cả data sources
- [ ] Estimate migration complexity
- [ ] Identify potential data quality issues

#### Ngày 3-5: Migration Tools Development
- [ ] Tạo `scripts/migration/migrate_to_unified_schema.py`
- [ ] Batch processing capability
- [ ] Progress tracking và logging
- [ ] Rollback mechanism

### Week 8: Migration Execution
#### Ngày 1: Full Backup
- [ ] Backup toàn bộ database
- [ ] Backup processed files
- [ ] Create restoration scripts

#### Ngày 2-4: Staged Migration
- [ ] Migration thử nghiệm với dataset nhỏ
- [ ] Validate migration results
- [ ] Full migration execution
- [ ] Data integrity checks

#### Ngày 5: Validation
- [ ] Compare old vs new data quality
- [ ] Embedding compatibility testing
- [ ] Search functionality validation

### Week 9: Post-Migration Validation
#### Ngày 1-3: Quality Assurance
- [ ] Comprehensive data quality checks
- [ ] Performance impact assessment
- [ ] User acceptance testing

#### Ngày 4-5: Optimization
- [ ] Performance tuning
- [ ] Index optimization
- [ ] Memory usage optimization

**Deliverables Phase 3**:
- ✅ Migration scripts và tools
- ✅ Migrated data với unified schema
- ✅ Data validation reports
- ✅ Rollback procedures

---

## 🔗 Phase 4: System Integration
**Timeline**: 3 tuần  
**Mục tiêu**: Cập nhật API và embedding system

### Week 10: API Updates
#### Ngày 1-2: API Schema Updates
- [ ] Update `app/api/schemas/` cho new format
- [ ] Maintain backwards compatibility
- [ ] API versioning implementation

#### Ngày 3-5: Endpoint Updates
- [ ] Update search endpoints
- [ ] Update retrieval logic
- [ ] Update response formatting

### Week 11: Embedding System
#### Ngày 1-3: Embedding Pipeline Updates
- [ ] Update `src/embedding/` modules
- [ ] Test embedding generation với new schema
- [ ] Performance optimization

#### Ngày 4-5: Vector Store Integration
- [ ] Update vector database integration
- [ ] Test similarity search functionality
- [ ] Index optimization

### Week 12: End-to-End Testing
#### Ngày 1-3: Integration Testing
- [ ] Full system testing
- [ ] API testing với real data
- [ ] Performance load testing

#### Ngày 4-5: User Acceptance Testing
- [ ] Test với real use cases
- [ ] Gather feedback từ users
- [ ] Bug fixes và improvements

**Deliverables Phase 4**:
- ✅ Updated API endpoints
- ✅ Updated embedding system
- ✅ Integration test results
- ✅ Performance benchmarks

---

## 📊 Phase 5: Monitoring & Launch
**Timeline**: 2 tuần  
**Mục tiêu**: Production deployment và monitoring

### Week 13: Monitoring Setup
#### Ngày 1-2: Monitoring Infrastructure
- [ ] Setup monitoring cho data quality
- [ ] Performance monitoring
- [ ] Error tracking và alerting

#### Ngày 3-5: Documentation
- [ ] User documentation updates
- [ ] API documentation
- [ ] Operational runbooks

### Week 14: Production Launch
#### Ngày 1-2: Soft Launch
- [ ] Deploy to staging environment
- [ ] Limited user testing
- [ ] Monitor system behavior

#### Ngày 3-5: Full Launch
- [ ] Production deployment
- [ ] Monitor system performance
- [ ] Gather user feedback
- [ ] Post-launch optimization

**Deliverables Phase 5**:
- ✅ Production system với unified schema
- ✅ Monitoring và alerting setup
- ✅ Updated documentation
- ✅ Launch success metrics

---

## ⚠️ Risk Management

### High-Impact Risks

#### 1. Data Loss During Migration
- **Probability**: Thấp
- **Impact**: Cao
- **Mitigation**: 
  - Full backup trước migration
  - Staged migration approach
  - Comprehensive rollback plan
  - Real-time monitoring

#### 2. Embedding System Breaking
- **Probability**: Trung bình
- **Impact**: Cao  
- **Mitigation**:
  - Thorough compatibility testing
  - Gradual rollout strategy
  - Fallback mechanism
  - A/B testing framework

### Medium-Impact Risks

#### 3. Performance Degradation
- **Probability**: Trung bình
- **Impact**: Trung bình
- **Mitigation**:
  - Performance benchmarking
  - Optimization sprints
  - Caching strategies
  - Infrastructure scaling

#### 4. API Backwards Compatibility
- **Probability**: Cao
- **Impact**: Trung bình
- **Mitigation**:
  - API versioning strategy
  - Gradual deprecation
  - Client update coordination
  - Comprehensive testing

---

## 🎯 Success Criteria

### Technical Metrics
- [ ] **Schema Consistency**: 100% của pipelines follow unified schema
- [ ] **Data Migration**: 0% data loss, <5% quality degradation  
- [ ] **Performance**: <20% increase trong processing time
- [ ] **API Compatibility**: Tất cả existing endpoints work với new data
- [ ] **Embedding Success**: >95% chunks successfully embedded

### Quality Metrics
- [ ] **Search Quality**: Maintain hoặc improve search relevance scores
- [ ] **User Satisfaction**: >90% user acceptance rate
- [ ] **System Stability**: <1% error rate post-launch
- [ ] **Documentation**: 100% API endpoints documented

---

## 👥 Resource Requirements

### Development Team
- **1 Senior Backend Developer** (full-time, 3 tháng)
  - Lead architecture design
  - Code pipeline updates
  - System integration
  
- **1 Data Engineer** (full-time, 2 tháng)  
  - Schema design
  - Migration scripts
  - Data quality validation
  
- **1 DevOps Engineer** (part-time, 1 tháng)
  - Infrastructure setup
  - Deployment automation
  - Monitoring setup
  
- **1 QA Engineer** (part-time, 1 tháng)
  - Test case development
  - Quality assurance
  - User acceptance testing

### Infrastructure Requirements
- **Development Environment**: Separate environment cho testing
- **Staging Environment**: Production-like setup
- **Storage**: Additional space cho backups (estimate 2x current data)
- **Monitoring Tools**: Grafana, Prometheus, ELK stack
- **Testing Infrastructure**: Load testing tools, automated testing

---

## 💰 Budget Estimate

### Personnel Costs (3.5 tháng)
- Senior Backend Developer: 3 tháng × $6,000 = $18,000
- Data Engineer: 2 tháng × $5,500 = $11,000  
- DevOps Engineer: 1 tháng × $5,000 = $5,000
- QA Engineer: 1 tháng × $4,000 = $4,000
- **Total Personnel**: $38,000

### Infrastructure Costs
- Additional cloud resources: $2,000
- Monitoring tools: $1,000
- Testing infrastructure: $1,500
- **Total Infrastructure**: $4,500

### **Total Project Cost**: $42,500

---

## 🚦 Go/No-Go Decision Points

### Phase 1 Checkpoint
- [ ] Schema design approved by all stakeholders
- [ ] Technical feasibility confirmed
- [ ] Resource allocation confirmed

### Phase 2 Checkpoint  
- [ ] All pipeline updates completed and tested
- [ ] Performance benchmarks meet criteria
- [ ] No critical bugs identified

### Phase 3 Checkpoint
- [ ] Migration successfully completed
- [ ] Data quality validation passed
- [ ] Rollback capability confirmed

### Phase 4 Checkpoint
- [ ] System integration successful
- [ ] API compatibility maintained
- [ ] Performance criteria met

---

## 📞 Communication Plan

### Weekly Status Reports
- **Audience**: Stakeholders, management
- **Content**: Progress, risks, blockers, next steps
- **Format**: Email summary + dashboard

### Bi-weekly Demos
- **Audience**: Development team, product owners
- **Content**: Working features, progress demonstration
- **Format**: Live demo + Q&A session

### Monthly Steering Committee
- **Audience**: Senior management, key stakeholders  
- **Content**: Strategic decisions, budget, timeline
- **Format**: Formal presentation

---

## 📚 Documentation Deliverables

### Technical Documentation
- [ ] Unified schema specification
- [ ] API documentation updates
- [ ] Migration procedures
- [ ] Operational runbooks

### User Documentation  
- [ ] User guide updates
- [ ] API integration examples
- [ ] Troubleshooting guide
- [ ] FAQ updates

### Project Documentation
- [ ] Lessons learned report
- [ ] Post-mortem analysis
- [ ] Knowledge transfer materials
- [ ] Maintenance procedures

---

## 🎉 Post-Launch Activities

### Week 1-2 Post-Launch
- [ ] System performance monitoring
- [ ] User feedback collection
- [ ] Bug triage và fixes
- [ ] Performance optimization

### Month 1 Post-Launch
- [ ] Comprehensive system review
- [ ] User satisfaction survey
- [ ] Performance analysis report
- [ ] Next iteration planning

### Ongoing Maintenance
- [ ] Regular schema updates
- [ ] Performance monitoring
- [ ] Data quality checks
- [ ] User support

---

## ✅ Approval & Sign-off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Project Manager | | | |
| Tech Lead | | | |  
| Data Engineering Lead | | | |
| Product Owner | | | |
| Senior Management | | | |

---

**Document Version History**:
- v1.0 (30/10/2025): Initial plan creation
- v1.1 (): Stakeholder feedback incorporation
- v1.2 (): Final approval version

**Next Review Date**: [To be determined after approval]