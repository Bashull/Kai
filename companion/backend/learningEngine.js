const { v4: uuid } = require('uuid');
const db = require('../database');
const fs = require('fs-extra');
const path = require('path');
const pdfParse = require('pdf-parse');

class LearningEngine {
  static async ingestFile(filePath, fileType = 'text') {
    const id = uuid();
    let content = '';

    try {
      if (fileType === 'pdf') {
        const buffer = await fs.readFile(filePath);
        const data = await pdfParse(buffer);
        content = data.text;
      } else if (fileType === 'text' || fileType === 'json' || fileType === 'md') {
        content = await fs.readFile(filePath, 'utf8');
      } else {
        throw new Error(`Unsupported file type: ${fileType}`);
      }

      // Generate simple embeddings (in production, use transformers/sentence-transformers)
      const embeddings = this.generateEmbeddings(content);

      await db.run(
        `INSERT INTO knowledge_base (id, source, content, embeddings, type) 
         VALUES (?, ?, ?, ?, ?)`,
        [id, path.basename(filePath), content.substring(0, 10000), JSON.stringify(embeddings), fileType]
      );

      return { id, source: path.basename(filePath), chunks: content.length };
    } catch (error) {
      console.error('Learning error:', error);
      throw error;
    }
  }

  static generateEmbeddings(text) {
    // Simple hashing for demo - replace with real embeddings in production
    const words = text.toLowerCase().split(/\s+/).slice(0, 100);
    return words.reduce((acc, word) => {
      acc[word] = (acc[word] || 0) + 1;
    }, {});
  }

  static async queryKnowledge(query, limit = 5) {
    const queryEmbeddings = this.generateEmbeddings(query);
    const knowledge = await db.all('SELECT * FROM knowledge_base LIMIT 100');

    // Simple relevance scoring
    const scored = knowledge.map(k => {
      const kEmbeddings = JSON.parse(k.embeddings || '{}');
      let score = 0;
      Object.keys(queryEmbeddings).forEach(word => {
        if (kEmbeddings[word]) score += queryEmbeddings[word] * kEmbeddings[word];
      });
      return { ...k, relevance: score };
    });

    return scored.sort((a, b) => b.relevance - a.relevance).slice(0, limit);
  }

  static async learnSkill(skillName, proficiency = 0.5, category = 'general') {
    const id = uuid();
    await db.run(
      `INSERT INTO skills (id, name, proficiency, category) 
       VALUES (?, ?, ?, ?)`,
      [id, skillName, proficiency, category]
    );
    return { id, skillName, proficiency };
  }

  static async improveSkill(skillId, increment = 0.1) {
    const skill = await db.get('SELECT * FROM skills WHERE id = ?', [skillId]);
    if (!skill) throw new Error('Skill not found');

    const newProficiency = Math.min(skill.proficiency + increment, 1.0);
    await db.run(
      'UPDATE skills SET proficiency = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
      [newProficiency, skillId]
    );

    return { skillId, newProficiency };
  }

  static async listSkills() {
    return db.all('SELECT * FROM skills ORDER BY proficiency DESC');
  }

  static async getKnowledgeStats() {
    const sources = await db.all(
      'SELECT COUNT(*) as count, type FROM knowledge_base GROUP BY type'
    );
    const totalSize = await db.get(
      'SELECT SUM(LENGTH(content)) as size FROM knowledge_base'
    );
    return { sources, totalSize };
  }
}

module.exports = LearningEngine;
